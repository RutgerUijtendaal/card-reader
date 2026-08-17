from __future__ import annotations

from typing import Any

from django.db import connections

from card_reader_core.models import CARD_POOLS, CardIdentityPoolLock


def ensure_card_identity_pool_locks(
    *,
    using: str,
    **_kwargs: Any,
) -> None:
    """Restore immutable pool lock rows after migrations and database flushes."""
    connection = connections[using]
    if CardIdentityPoolLock._meta.db_table not in connection.introspection.table_names():
        return
    CardIdentityPoolLock.objects.using(using).bulk_create(
        [CardIdentityPoolLock(card_pool=card_pool) for card_pool in CARD_POOLS],
        ignore_conflicts=True,
    )
