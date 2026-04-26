# Card Reader Core

Shared runtime, Django settings, domain models, repositories, and business services used by API and
parser services.

`card_reader_core.django_settings` is the neutral Django settings module for non-HTTP processes
such as the parser. API-specific settings, URLs, DRF configuration, and CORS stay in
`card_reader_api.project.settings`, the only Django project package.
