from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .calendar_sync import (
    delete_from_external_calendars,
    sync_event_to_caldav,
    sync_event_to_google,
)
from .models import CalendarEvent


@receiver(post_save, sender=CalendarEvent)
def handle_calendar_event_save(sender, instance, created, **kwargs):
    """Sync event to external calendars on save."""
    sync_event_to_google(instance)
    sync_event_to_caldav(instance)


@receiver(post_delete, sender=CalendarEvent)
def handle_calendar_event_delete(sender, instance, **kwargs):
    """Remove event from external calendars on delete."""
    delete_from_external_calendars(instance)
