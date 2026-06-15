from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from card_reader_core.models import UserAccessRequest

ACCESS_REQUEST_ALL_STATUS = "all"
AccessRequestStatusFilter = Literal["pending", "all"]


@dataclass(frozen=True)
class AccessRequestSubmission:
    access_request: UserAccessRequest
    created: bool
