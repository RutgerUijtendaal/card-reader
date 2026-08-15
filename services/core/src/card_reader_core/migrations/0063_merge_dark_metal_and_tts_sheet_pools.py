from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from django.db import migrations
from django.db.migrations.operations.base import Operation


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0062_dark_and_metal_factions"),
        ("card_reader_core", "0062_pool_partitioned_tts_card_sheets"),
    ]

    operations: ClassVar[Sequence[Operation]] = []
