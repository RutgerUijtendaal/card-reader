# Card Reader Parser

Background parser process polling queued import jobs through the core Django data layer.

The parser boots Django with `card_reader_core.django_settings` and must not import API
views, serializers, URLs, or API-only services.
