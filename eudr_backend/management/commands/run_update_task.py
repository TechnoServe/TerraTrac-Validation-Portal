# farm/management/commands/run_update_task.py

from django.core.management.base import BaseCommand
from ...tasks import update_farm_geoid
import time


class Command(BaseCommand):
    help = 'Run the update_farm_geoid task every 5 minutes'

    def handle(self, *args, **kwargs):
        while True:
            update_farm_geoid.delay()  # Schedule the task asynchronously
            self.stdout.write(self.style.SUCCESS(
                'Successfully scheduled the task'))
            time.sleep(300)  # Sleep for 5 minutes
