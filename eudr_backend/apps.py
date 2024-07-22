from django.apps import AppConfig
import threading
import os


class FarmConfig(AppConfig):
    name = 'eudr_backend'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            from django.core.management import call_command
            thread = threading.Thread(
                target=call_command, args=('run_update_task',))
            thread.start()
