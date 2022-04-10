import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps


class OccasionsConfig(AppConfig):
    name = "attendees.occasions"

    def ready(self):
        schedule_calendar_model = django_apps.get_model("schedule.Calendar", require_ready=False)
        schedule_calendarrelation_model = django_apps.get_model("schedule.CalendarRelation", require_ready=False)
        schedule_event_model = django_apps.get_model("schedule.Event", require_ready=False)
        schedule_eventrelation_model = django_apps.get_model("schedule.EventRelation", require_ready=False)

        pghistory.track(
            pghistory.Snapshot('calendar.snapshot'),
            related_name='history',
            model_name='CalendarHistory',
            app_label='occasions'
        )(schedule_calendar_model)

        pghistory.track(
            pghistory.Snapshot('calendarrelation.snapshot'),
            related_name='history',
            model_name='CalendarRelationHistory',
            app_label='occasions',
        )(schedule_calendarrelation_model)

        pghistory.track(
            pghistory.Snapshot('event.snapshot'),
            related_name='history',
            model_name='EventHistory',
            app_label='occasions'
        )(schedule_event_model)

        pghistory.track(
            pghistory.Snapshot('eventrelation.snapshot'),
            related_name='history',
            model_name='EventRelationHistory',
            app_label='occasions',
        )(schedule_eventrelation_model)
