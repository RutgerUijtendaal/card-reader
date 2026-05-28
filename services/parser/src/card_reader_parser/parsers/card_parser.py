from __future__ import annotations

import logging
from pathlib import Path

from ..extractors import KnownMetadataExtractor
from card_reader_core.models import Keyword, Symbol, Tag, Type
from card_reader_core.services.templates import TemplateService
from card_reader_core.config.settings import settings
from card_reader_core.storage import calculate_checksum

from .ocr_runner import OcrRunner
from .region_cropper import RegionCrop, RegionCropper
from .regions import (
    AffinityParser,
    NameManaCostParser,
    RegionParseResult,
    RulesTextParser,
    StatsRegionParser,
    TypeTagParser,
)
from .symbol_detector import SymbolDetector
from .types import ParsedCard, ParsedMetadataSuggestion

logger = logging.getLogger(__name__)

NAME_MANA_COST = "name_mana_cost"
TYPE_TAG = "type_tag"
RULES_TEXT = "rules_text"
ATTACK = "attack"
HEALTH = "health"
AFFINITY = "affinity"


class CardParser:
    def __init__(self) -> None:
        self._template_service = TemplateService()
        self._cropper = RegionCropper()
        self._ocr_runner = OcrRunner()
        self._symbol_detector = SymbolDetector()
        self._metadata_extractor = KnownMetadataExtractor()
        self._name_mana_cost_parser = NameManaCostParser(self._ocr_runner, self._symbol_detector)
        self._type_tag_parser = TypeTagParser(self._ocr_runner, self._metadata_extractor)
        self._rules_text_parser = RulesTextParser(
            self._ocr_runner, self._symbol_detector, self._metadata_extractor
        )
        self._affinity_parser = AffinityParser(self._symbol_detector)
        self._stats_region_parser = StatsRegionParser(self._ocr_runner)

    def parse(
        self,
        image_path: Path,
        template_id: str,
        symbols: list[Symbol] | None = None,
        known_keywords: list[Keyword] | None = None,
        known_tags: list[Tag] | None = None,
        known_types: list[Type] | None = None,
    ) -> ParsedCard:
        logger.info(
            "Card parse started. image_path=%s template_id=%s symbols=%s known_keywords=%s",
            image_path,
            template_id,
            0 if symbols is None else len(symbols),
            0 if known_keywords is None else len(known_keywords),
        )
        template = self._template_service.get_template_definition(template_id)
        checksum = calculate_checksum(image_path)
        region_crops = self._cropper.crop_regions(image_path=image_path, template=template)
        logger.info(
            "Card regions cropped. image_path=%s template_id=%s regions=%s",
            image_path,
            template_id,
            sorted(region_crops.keys()),
        )

        if settings.save_debug_crops:
            self._cropper.write_debug_crops(
                template_id=template_id,
                checksum=checksum,
                image_path=image_path,
                region_crops=region_crops,
            )

        symbols = symbols or []
        known_keywords = known_keywords or []
        known_tags = known_tags or []
        known_types = known_types or []
        region_results: dict[str, RegionParseResult] = {}
        semantic_results: dict[str, RegionParseResult] = {}
        rules_text_primary: RegionParseResult | None = None
        regions_spec = template.get("regions", [])
        for region_spec in regions_spec:
            if not isinstance(region_spec, dict):
                continue
            region_id = str(region_spec.get("region_id", "")).strip()
            parser_type = str(region_spec.get("parser_type", "")).strip()
            if not region_id or region_id not in region_crops:
                continue

            if parser_type == RULES_TEXT and rules_text_primary is not None and rules_text_primary.text:
                continue

            result = self._parse_region(
                parser_type=parser_type,
                region_id=region_id,
                image_path=image_path,
                region_spec=region_spec,
                region_crops=region_crops,
                symbols=symbols,
                known_keywords=known_keywords,
                known_tags=known_tags,
                known_types=known_types,
            )
            if result is None:
                continue

            region_results[region_id] = result
            if parser_type != RULES_TEXT or not rules_text_primary or not rules_text_primary.text:
                semantic_results[parser_type] = result
            if parser_type == RULES_TEXT and rules_text_primary is None:
                rules_text_primary = result

        normalized_fields = self._merge_normalized_fields(region_results, image_path)
        confidence = self._confidence_breakdown(semantic_results)
        keyword_ids = self._merge_keyword_ids(region_results)
        tag_ids = self._merge_tag_ids(region_results)
        type_ids = self._merge_type_ids(region_results)
        symbol_ids = self._merge_symbol_ids(region_results)
        tag_suggestions = self._merge_tag_suggestions(region_results)
        type_suggestions = self._merge_type_suggestions(region_results)

        raw_ocr = {
            "template": template,
            "regions": {
                region_name: {
                    "bbox": {
                        "x": crop["x"],
                        "y": crop["y"],
                        "w": crop["w"],
                        "h": crop["h"],
                    },
                    "text": region_results.get(region_name, RegionParseResult(region_name)).text,
                    "confidence": region_results.get(region_name, RegionParseResult(region_name)).confidence,
                    "lines": region_results.get(region_name, RegionParseResult(region_name)).lines,
                    "symbols": [
                        item.to_dict()
                        for item in region_results.get(region_name, RegionParseResult(region_name)).detected_symbols
                    ],
                    "normalized_fields": region_results.get(
                        region_name, RegionParseResult(region_name)
                    ).normalized_fields,
                    "debug_crop_written": bool(settings.save_debug_crops),
                }
                for region_name, crop in region_crops.items()
            },
            "notes": "PaddleOCR region OCR",
        }

        logger.info(
            "Card parse finished. image_path=%s checksum=%s overall_conf=%.3f fields=%s symbols=%s keywords=%s tags=%s types=%s",
            image_path,
            checksum,
            float(confidence.get("overall", 0.0)),
            sorted(normalized_fields.keys()),
            len(symbol_ids),
            len(keyword_ids),
            len(tag_ids),
            len(type_ids),
        )
        return ParsedCard(
            checksum=checksum,
            normalized_fields=normalized_fields,
            confidence=confidence,
            raw_ocr=raw_ocr,
            keyword_ids=keyword_ids,
            tag_ids=tag_ids,
            type_ids=type_ids,
            symbol_ids=symbol_ids,
            tag_suggestions=tag_suggestions,
            type_suggestions=type_suggestions,
        )

    def _parse_region(
        self,
        *,
        parser_type: str,
        region_id: str,
        image_path: Path,
        region_spec: dict[str, object],
        region_crops: dict[str, RegionCrop],
        symbols: list[Symbol],
        known_keywords: list[Keyword],
        known_tags: list[Tag],
        known_types: list[Type],
    ) -> RegionParseResult | None:
        image = region_crops[region_id]["image"]
        if parser_type == NAME_MANA_COST:
            result = self._name_mana_cost_parser.parse(
                region_name=region_id,
                image=image,
                image_stem=image_path.stem,
                region_spec=region_spec,
                symbols=symbols,
            )
            logger.info(
                "Region parsed successfully. region=%s parser_type=%s conf=%.3f text_len=%s fields=%s symbols=%s",
                region_id,
                parser_type,
                result.confidence,
                len(result.text),
                sorted(result.normalized_fields.keys()),
                len(result.detected_symbols),
            )
            return result

        if parser_type == TYPE_TAG:
            result = self._type_tag_parser.parse(
                region_name=region_id,
                image=image,
                region_spec=region_spec,
                known_tags=known_tags,
                known_types=known_types,
            )
            logger.info(
                "Region parsed successfully. region=%s parser_type=%s conf=%.3f text_len=%s tags=%s types=%s fields=%s",
                region_id,
                parser_type,
                result.confidence,
                len(result.text),
                len(result.extracted_tag_ids),
                len(result.extracted_type_ids),
                sorted(result.normalized_fields.keys()),
            )
            return result

        if parser_type == RULES_TEXT:
            result = self._rules_text_parser.parse(
                region_name=region_id,
                image=image,
                region_spec=region_spec,
                symbols=symbols,
                known_keywords=known_keywords,
            )
            logger.info(
                "Region parsed successfully. region=%s parser_type=%s conf=%.3f text_len=%s keywords=%s symbols=%s fields=%s",
                region_id,
                parser_type,
                result.confidence,
                len(result.text),
                len(result.extracted_keyword_ids),
                len(result.detected_symbols),
                sorted(result.normalized_fields.keys()),
            )
            return result

        if parser_type == AFFINITY:
            result = self._affinity_parser.parse(
                region_name=region_id,
                image=image,
                region_spec=region_spec,
                symbols=symbols,
            )
            logger.info(
                "Region parsed successfully. region=%s parser_type=%s conf=%.3f symbols=%s fields=%s",
                region_id,
                parser_type,
                result.confidence,
                len(result.detected_symbols),
                sorted(result.normalized_fields.keys()),
            )
            return result

        if parser_type == ATTACK:
            result = self._stats_region_parser.parse(
                region_name=region_id,
                field_name="attack",
                image=image,
                region_spec=region_spec,
            )
            logger.info(
                "Region parsed successfully. region=%s parser_type=%s conf=%.3f text_len=%s fields=%s",
                region_id,
                parser_type,
                result.confidence,
                len(result.text),
                sorted(result.normalized_fields.keys()),
            )
            return result

        if parser_type == HEALTH:
            result = self._stats_region_parser.parse(
                region_name=region_id,
                field_name="health",
                image=image,
                region_spec=region_spec,
            )
            logger.info(
                "Region parsed successfully. region=%s parser_type=%s conf=%.3f text_len=%s fields=%s",
                region_id,
                parser_type,
                result.confidence,
                len(result.text),
                sorted(result.normalized_fields.keys()),
            )
            return result

        return None

    def _merge_normalized_fields(
        self,
        region_results: dict[str, RegionParseResult],
        image_path: Path,
    ) -> dict[str, str]:
        merged: dict[str, str] = {}
        for result in region_results.values():
            merged.update(result.normalized_fields)

        name = merged.get("name", "").strip()
        if not name:
            merged["name"] = image_path.stem
        merged.setdefault("type_line", "")
        merged.setdefault("mana_cost", "")
        merged.setdefault("mana_symbols", "")
        merged.setdefault("mana_total", "")
        merged.setdefault("rules_text_raw", "")
        merged.setdefault("rules_text_enriched", "")
        merged.setdefault("rules_text", "")
        return merged

    def _confidence_breakdown(self, semantic_results: dict[str, RegionParseResult]) -> dict[str, float]:
        name_conf = semantic_results.get(NAME_MANA_COST, RegionParseResult(NAME_MANA_COST)).confidence
        type_conf = semantic_results.get(TYPE_TAG, RegionParseResult(TYPE_TAG)).confidence
        rules_conf = semantic_results.get(RULES_TEXT, RegionParseResult(RULES_TEXT)).confidence
        attack_conf = semantic_results.get(ATTACK, RegionParseResult(ATTACK)).confidence
        health_conf = semantic_results.get(HEALTH, RegionParseResult(HEALTH)).confidence

        present_conf = [v for v in [name_conf, type_conf, rules_conf, attack_conf, health_conf] if v > 0.0]
        overall = float(sum(present_conf) / len(present_conf)) if present_conf else 0.0

        return {
            "name": round(name_conf, 3),
            "type_line": round(type_conf, 3),
            "mana_cost": round(name_conf, 3),
            "rules_text": round(rules_conf, 3),
            "attack": round(attack_conf, 3),
            "health": round(health_conf, 3),
            "overall": round(overall, 3),
        }

    def _merge_keyword_ids(self, region_results: dict[str, RegionParseResult]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for result in region_results.values():
            for keyword_id in result.extracted_keyword_ids:
                if keyword_id in seen:
                    continue
                seen.add(keyword_id)
                out.append(keyword_id)
        return out

    def _merge_tag_ids(self, region_results: dict[str, RegionParseResult]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for result in region_results.values():
            for tag_id in result.extracted_tag_ids:
                if tag_id in seen:
                    continue
                seen.add(tag_id)
                out.append(tag_id)
        return out

    def _merge_type_ids(self, region_results: dict[str, RegionParseResult]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for result in region_results.values():
            for type_id in result.extracted_type_ids:
                if type_id in seen:
                    continue
                seen.add(type_id)
                out.append(type_id)
        return out

    def _merge_symbol_ids(self, region_results: dict[str, RegionParseResult]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for result in region_results.values():
            for row in result.detected_symbols:
                if row.symbol_id in seen:
                    continue
                seen.add(row.symbol_id)
                out.append(row.symbol_id)
        return out

    def _merge_tag_suggestions(self, region_results: dict[str, RegionParseResult]) -> list[ParsedMetadataSuggestion]:
        return self._merge_suggestions(region_results, kind="tag")

    def _merge_type_suggestions(self, region_results: dict[str, RegionParseResult]) -> list[ParsedMetadataSuggestion]:
        return self._merge_suggestions(region_results, kind="type")

    def _merge_suggestions(
        self,
        region_results: dict[str, RegionParseResult],
        *,
        kind: str,
    ) -> list[ParsedMetadataSuggestion]:
        out: list[ParsedMetadataSuggestion] = []
        seen: set[str] = set()
        for result in region_results.values():
            candidates = (
                result.extracted_tag_suggestions
                if kind == "tag"
                else result.extracted_type_suggestions
            )
            for candidate in candidates:
                if candidate.normalized_value in seen:
                    continue
                seen.add(candidate.normalized_value)
                out.append(candidate)
        return out
