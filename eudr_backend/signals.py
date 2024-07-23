import logging
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .tasks import update_geoid


@receiver(post_migrate)
def schedule_update_geoid(sender, **kwargs):
    print("Scheduling update_geoid task")
    update_geoid(repeat=300)  # Schedule to run every 5 minutes
