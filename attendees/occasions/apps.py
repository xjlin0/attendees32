import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps


class OccasionsConfig(AppConfig):
    name = "attendees.occasions"

    def ready(self):
        schedule_event_model = django_apps.get_model("schedule.Event", require_ready=False)

        pghistory.track(
            pghistory.Snapshot('event.snapshot'),
            app_label='occasions'
        )(schedule_event_model)
