from django.apps import AppConfig


class EudrBackendConfig(AppConfig):
    name = 'eudr_backend'

    def ready(self):
        import eudr_backend.signals
