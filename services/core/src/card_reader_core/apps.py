from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CardReaderCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "card_reader_core"
    label = "card_reader_core"
    verbose_name = "Card Reader Core"

    def ready(self) -> None:
        from card_reader_core.services.cards.identity_locks import ensure_card_identity_pool_locks

        post_migrate.connect(
            ensure_card_identity_pool_locks,
            sender=self,
            dispatch_uid="card_reader_core.ensure_card_identity_pool_locks",
            weak=False,
        )
