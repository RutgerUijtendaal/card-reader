from __future__ import annotations

import logging
from pathlib import Path

from ..extractors import KnownMetadataExtractor
from card_reader_core.models import Keyword, Symbol, Tag, Type
from card_reader_core.services.templates import TemplateService
from card_reader_core.settings import settings
from card_reader_core.storage import calculate_checksum

from .ocr_runner import OcrRunner
from .regions import (
    BottomRegionParser,
    AffinityRegionParser,
    MiddleRegionParser,
    RegionParseResult,
    StatsRegionParser,
    TopRegionParser,
)
from .region_cropper import RegionCropper
from .symbol_detector import SymbolDetector
from .types import ParsedCard

logger = logging.getLogger(__name__)


class CardParser:
    def __init__(self) -> None:
        self._template_service = TemplateService()
        self._cropper = RegionCropper()
        self._ocr_runner = OcrRunner()
        self._symbol_detector = SymbolDetector()
        self._metadata_extractor = KnownMetadataExtractor()
        self._top_region_parser = TopRegionParser(self._ocr_runner, self._symbol_detector)
        self._middle_region_parser = MiddleRegionParser(self._ocr_runner, self._metadata_extractor)
        self._bottom_region_parser = BottomRegionParser(
            self._ocr_runner, self._symbol_detector, self._metadata_extractor
        )
        self._affinity_region_parser = AffinityRegionParser(self._symbol_detector)
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
        regions_spec = template.get("regions", {})

        region_results: dict[str, RegionParseResult] = {}
        if "top_bar" in region_crops:
            region_results["top_bar"] = self._top_region_parser.parse(
                region_name="top_bar",
                image=region_crops["top_bar"]["image"],
                image_stem=image_path.stem,
                region_spec=regions_spec.get("top_bar", {}),
                symbols=symbols,
            )
            top_result = region_results["top_bar"]
            logger.info(
                "Region parsed successfully. region=top_bar conf=%.3f text_len=%s fields=%s symbols=%s",
                top_result.confidence,
                len(top_result.text),
                sorted(top_result.normalized_fields.keys()),
                len(top_result.detected_symbols),
            )
        if "type_bar" in region_crops:
            region_results["type_bar"] = self._middle_region_parser.parse(
                region_name="type_bar",
                image=region_crops["type_bar"]["image"],
                region_spec=regions_spec.get("type_bar", {}),
                known_tags=known_tags,
                known_types=known_types,
            )
            middle_result = region_results["type_bar"]
            logger.info(
                "Region parsed successfully. region=type_bar conf=%.3f text_len=%s tags=%s types=%s fields=%s",
                middle_result.confidence,
                len(middle_result.text),
                len(middle_result.extracted_tag_ids),
                len(middle_result.extracted_type_ids),
                sorted(middle_result.normalized_fields.keys()),
            )
        if "rules_text" in region_crops:
            region_results["rules_text"] = self._bottom_region_parser.parse(
                region_name="rules_text",
                image=region_crops["rules_text"]["image"],
                region_spec=regions_spec.get("rules_text", {}),
                symbols=symbols,
                known_keywords=known_keywords,
            )
            bottom_result = region_results["rules_text"]
            logger.info(
                "Region parsed successfully. region=rules_text conf=%.3f text_len=%s keywords=%s symbols=%s fields=%s",
                bottom_result.confidence,
                len(bottom_result.text),
                len(bottom_result.extracted_keyword_ids),
                len(bottom_result.detected_symbols),
                sorted(bottom_result.normalized_fields.keys()),
            )
        if "bottom_middle" in region_crops:
            region_results["bottom_middle"] = self._affinity_region_parser.parse(
                region_name="bottom_middle",
                image=region_crops["bottom_middle"]["image"],
                region_spec=regions_spec.get("bottom_middle", {}),
                symbols=symbols,
            )
            affinity_result = region_results["bottom_middle"]
            logger.info(
                "Region parsed successfully. region=bottom_middle conf=%.3f symbols=%s fields=%s",
                affinity_result.confidence,
                len(affinity_result.detected_symbols),
                sorted(affinity_result.normalized_fields.keys()),
            )
        if "bottom_left" in region_crops:
            region_results["bottom_left"] = self._stats_region_parser.parse(
                region_name="bottom_left",
                field_name="attack",
                image=region_crops["bottom_left"]["image"],
                region_spec=regions_spec.get("bottom_left", {}),
            )
            attack_result = region_results["bottom_left"]
            logger.info(
                "Region parsed successfully. region=bottom_left conf=%.3f text_len=%s fields=%s",
                attack_result.confidence,
                len(attack_result.text),
                sorted(attack_result.normalized_fields.keys()),
            )
        if "bottom_right" in region_crops:
            region_results["bottom_right"] = self._stats_region_parser.parse(
                region_name="bottom_right",
                field_name="health",
                image=region_crops["bottom_right"]["image"],
                region_spec=regions_spec.get("bottom_right", {}),
            )
            health_result = region_results["bottom_right"]
            logger.info(
                "Region parsed successfully. region=bottom_right conf=%.3f text_len=%s fields=%s",
                health_result.confidence,
                len(health_result.text),
                sorted(health_result.normalized_fields.keys()),
            )

        normalized_fields = self._merge_normalized_fields(region_results, image_path)
        confidence = self._confidence_breakdown(region_results)
        keyword_ids = self._merge_keyword_ids(region_results)
        tag_ids = self._merge_tag_ids(region_results)
        type_ids = self._merge_type_ids(region_results)
        symbol_ids = self._merge_symbol_ids(region_results)

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
        )

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

    def _confidence_breakdown(self, region_results: dict[str, RegionParseResult]) -> dict[str, float]:
        name_conf = region_results.get("top_bar", RegionParseResult("top_bar")).confidence
        type_conf = region_results.get("type_bar", RegionParseResult("type_bar")).confidence
        rules_conf = region_results.get("rules_text", RegionParseResult("rules_text")).confidence
        attack_conf = region_results.get("bottom_left", RegionParseResult("bottom_left")).confidence
        health_conf = region_results.get("bottom_right", RegionParseResult("bottom_right")).confidence

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
