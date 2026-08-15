from __future__ import annotations

from dataclasses import dataclass
import time
from collections.abc import Callable

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
    list_out_of_pool_card_ids_on_sheet,
    list_sheet_ids_needing_render,
    list_usable_card_sources,
    prioritize_sheets,
    refresh_card_source_visibility,
    refresh_sheet_source_visibility,
    release_expired_render_claims,
    request_sheet_rerender,
    sheet_has_incompatible_slots,
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
        affected_sheet_ids = sync_card_sources(list_usable_card_sources(normalized_ids))
        affected_sheet_ids.update(refresh_card_source_visibility(normalized_ids))
        return affected_sheet_ids

    def ensure_sheet_current(self, sheet_id: str) -> bool:
        if not sheet_has_incompatible_slots(sheet_id):
            return True
        out_of_pool_card_ids = list_out_of_pool_card_ids_on_sheet(sheet_id)
        if out_of_pool_card_ids:
            self.sync_cards(out_of_pool_card_ids)
        refresh_sheet_source_visibility(sheet_id)
        return sheet_id not in list_sheet_ids_needing_render([sheet_id])

    def reconcile_all(
        self,
        *,
        render: bool = False,
        force: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> TtsCardSheetReconciliationResult:
        _report_progress(progress, "Scanning card images for pool-partitioned TTS sheet assignments...")
        usable_cards = 0
        assigned_cards = 0
        affected_sheet_ids = upgrade_sheet_layouts()
        all_sheet_ids = set(list_all_sheet_ids())
        affected_sheet_ids.update(refresh_card_source_visibility())
        for sources in iter_usable_card_source_batches():
            card_ids = [source.card.id for source in sources]
            usable_cards += len(sources)
            affected_sheet_ids.update(sync_card_sources(sources))
            assignments = get_card_sheet_assignments(card_ids)
            assigned_cards += len(assignments)
            all_sheet_ids.update(row.sheet_id for row in assignments.values())
            _report_progress(
                progress,
                f"Prepared {usable_cards} usable card images and {assigned_cards} assignments...",
            )
        missing_sheet_ids = self._unavailable_sheet_ids(list(all_sheet_ids))
        request_sheet_rerender(missing_sheet_ids)
        affected_sheet_ids.update(missing_sheet_ids)
        if force:
            request_sheet_rerender(list(all_sheet_ids))
            affected_sheet_ids.update(all_sheet_ids)
        affected_sheet_ids.update(list_sheet_ids_needing_render(list(all_sheet_ids)))
        _report_progress(
            progress,
            f"TTS assignment complete: {assigned_cards} cards across {len(all_sheet_ids)} sheets; "
            f"{len(affected_sheet_ids)} sheets need work.",
        )
        rendered_count = (
            self.render_sheets_now(sorted(affected_sheet_ids), progress=progress)
            if render
            else 0
        )
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
        progress: Callable[[str], None] | None = None,
    ) -> int:
        rendered = 0
        unique_sheet_ids = list(dict.fromkeys(sheet_ids))
        total_sheets = len(unique_sheet_ids)
        for position, sheet_id in enumerate(unique_sheet_ids, start=1):
            while sheet_id in list_sheet_ids_needing_render([sheet_id]):
                claimed = claim_sheet_for_render(
                    sheet_id,
                    respect_not_before=respect_not_before,
                )
                if claimed is None:
                    break
                _report_progress(
                    progress,
                    f"Rendering TTS card sheet {position}/{total_sheets}...",
                )
                render_claimed_sheet(claimed)
                rendered += 1
                _report_progress(
                    progress,
                    f"Rendered TTS card sheet {position}/{total_sheets}.",
                )
        if unique_sheet_ids:
            _report_progress(
                progress,
                f"TTS rendering complete: {rendered} sheet revisions rendered.",
            )
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


def _report_progress(progress: Callable[[str], None] | None, message: str) -> None:
    if progress is not None:
        progress(message)


__all__ = [
    "TtsCardSheetPreparationError",
    "TtsCardSheetReconciliationResult",
    "TtsCardSheetService",
]
