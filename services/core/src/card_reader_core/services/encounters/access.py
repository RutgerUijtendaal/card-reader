from __future__ import annotations

from dataclasses import dataclass

from card_reader_core.models.encounter import Encounter


@dataclass(frozen=True)
class EncounterActor:
    user_id: str | None = None
    is_staff: bool = False

    def owns(self, encounter: Encounter) -> bool:
        return self.user_id == str(encounter.creator_id)

    def can_manage(self, encounter: Encounter) -> bool:
        return self.is_staff or (self.owns(encounter) and not encounter.is_official)

    def can_inspect(self, encounter: Encounter) -> bool:
        return self.is_staff or self.owns(encounter)
