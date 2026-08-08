from __future__ import annotations

from dataclasses import dataclass
import time

from django.db import transaction

from card_reader_core.config.settings import settings
from card_reader_core.repositories.tts_card_sheets import (
    TtsCardSheetAssignment,
    claim_sheet_for_render,
    ensure_sheet_render_requested,
    get_card_sheet_assignments,
    get_sheet_rendered_checksums,
    iter_usable_card_source_batches,
    list_all_sheet_ids,
    list_sheet_ids_needing_render,
    list_usable_card_sources,
    prioritize_sheets,
    release_expired_render_claims,
    request_sheet_rerender,
    sync_card_sources,
    sync_merged_card_source,
    upgrade_sheet_layouts,
)

from .renderer import TtsCardSheetRenderError, render_claimed_sheet, tts_card_sheet_path


@dataclass(frozen=True)
class TtsCardSheetReconciliationResult:
    usable_cards: int
    assigned_cards: int
    affected_sheets: int
    rendered_sheets: int


class TtsCardSheetPreparationError(RuntimeError):
    pass


class TtsCardSheetService:
    def sync_cards(self, card_ids: list[str]) -> set[str]:
        normalized_ids = list(dict.fromkeys(card_ids))
        if not normalized_ids:
            return set()
        return sync_card_sources(list_usable_card_sources(normalized_ids))

    def reconcile_all(
        self,
        *,
        render: bool = False,
        force: bool = False,
    ) -> TtsCardSheetReconciliationResult:
        usable_cards = 0
        assigned_cards = 0
        affected_sheet_ids = upgrade_sheet_layouts()
        all_sheet_ids = set(list_all_sheet_ids())
        for sources in iter_usable_card_source_batches():
            card_ids = [source.card.id for source in sources]
            usable_cards += len(sources)
            affected_sheet_ids.update(sync_card_sources(sources))
            assignments = get_card_sheet_assignments(card_ids)
            assigned_cards += len(assignments)
            all_sheet_ids.update(row.sheet_id for row in assignments.values())
        missing_sheet_ids = self._unavailable_sheet_ids(list(all_sheet_ids))
        request_sheet_rerender(missing_sheet_ids)
        affected_sheet_ids.update(missing_sheet_ids)
        if force:
            request_sheet_rerender(list(all_sheet_ids))
            affected_sheet_ids.update(all_sheet_ids)
        affected_sheet_ids.update(list_sheet_ids_needing_render(list(all_sheet_ids)))
        rendered_count = self.render_sheets_now(sorted(affected_sheet_ids)) if render else 0
        return TtsCardSheetReconciliationResult(
            usable_cards=usable_cards,
            assigned_cards=assigned_cards,
            affected_sheets=len(affected_sheet_ids),
            rendered_sheets=rendered_count,
        )

    def sync_merge(self, *, target_card_id: str, source_card_ids: list[str]) -> set[str]:
        target_sources = list_usable_card_sources([target_card_id])
        affected_sheet_ids = sync_merged_card_source(
            source_card_ids=source_card_ids,
            target_card_id=target_card_id,
            target_source=target_sources[0] if target_sources else None,
        )
        transaction.on_commit(lambda: self.sync_cards([target_card_id]))
        return affected_sheet_ids

    def prepare_cards(
        self,
        card_ids: list[str],
        *,
        timeout_seconds: float = 30.0,
    ) -> dict[str, TtsCardSheetAssignment]:
        self.sync_cards(card_ids)
        assignments = get_card_sheet_assignments(card_ids)
        sheet_ids = list(dict.fromkeys(row.sheet_id for row in assignments.values()))
        missing_sheet_ids = self._unavailable_sheet_ids(sheet_ids)
        request_sheet_rerender(missing_sheet_ids)
        prioritize_sheets(sheet_ids)
        if settings.is_dev:
            try:
                self.render_sheets_now(sheet_ids, respect_not_before=True)
            except TtsCardSheetRenderError as exc:
                raise TtsCardSheetPreparationError(
                    "One or more TTS card sheets could not be rendered. Try the export again shortly."
                ) from exc
            self._wait_until_ready(sheet_ids, timeout_seconds=timeout_seconds)
        else:
            self._require_ready(sheet_ids)
        return get_card_sheet_assignments(card_ids)

    def request_render(self, sheet_id: str, *, force: bool = False) -> None:
        if force:
            request_sheet_rerender([sheet_id])
        else:
            ensure_sheet_render_requested([sheet_id])

    def recover_renderer(self) -> TtsCardSheetReconciliationResult:
        release_expired_render_claims()
        return self.reconcile_all(render=False)

    def render_sheets_now(
        self,
        sheet_ids: list[str],
        *,
        respect_not_before: bool = False,
    ) -> int:
        rendered = 0
        for sheet_id in list(dict.fromkeys(sheet_ids)):
            while sheet_id in list_sheet_ids_needing_render([sheet_id]):
                claimed = claim_sheet_for_render(
                    sheet_id,
                    respect_not_before=respect_not_before,
                )
                if claimed is None:
                    break
                render_claimed_sheet(claimed)
                rendered += 1
        return rendered

    def _wait_until_ready(self, sheet_ids: list[str], *, timeout_seconds: float) -> None:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while True:
            pending = list_sheet_ids_needing_render(sheet_ids)
            unavailable = self._unavailable_sheet_ids(sheet_ids)
            if not pending and not unavailable:
                return
            if time.monotonic() >= deadline:
                raise TtsCardSheetPreparationError(
                    "One or more TTS card sheets are still being prepared. Try the export again shortly."
                )
            time.sleep(0.1)

    def _require_ready(self, sheet_ids: list[str]) -> None:
        pending = list_sheet_ids_needing_render(sheet_ids)
        unavailable = self._unavailable_sheet_ids(sheet_ids)
        if pending or unavailable:
            raise TtsCardSheetPreparationError(
                "One or more TTS card sheets are still being prepared. Try the export again shortly."
            )

    @staticmethod
    def _unavailable_sheet_ids(sheet_ids: list[str]) -> list[str]:
        rendered_checksums = get_sheet_rendered_checksums(sheet_ids)
        return [
            sheet_id
            for sheet_id in sheet_ids
            if not rendered_checksums.get(sheet_id)
            or not tts_card_sheet_path(sheet_id, rendered_checksums[sheet_id]).is_file()
        ]


__all__ = [
    "TtsCardSheetPreparationError",
    "TtsCardSheetReconciliationResult",
    "TtsCardSheetService",
]
