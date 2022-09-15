import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps


class OccasionsConfig(AppConfig):
    name = "attendees.occasions"

    def ready(self): #
        celery_task_model = django_apps.get_model("django_celery_beat.periodictask", require_ready=False)
        schedule_calendar_model = django_apps.get_model("schedule.Calendar", require_ready=False)
        schedule_calendarrelation_model = django_apps.get_model("schedule.CalendarRelation", require_ready=False)
        schedule_event_model = django_apps.get_model("schedule.Event", require_ready=False)
        schedule_eventrelation_model = django_apps.get_model("schedule.EventRelation", require_ready=False)
        schedule_rule_model = django_apps.get_model("schedule.Rule", require_ready=False)

        @pghistory.track(
            pghistory.Snapshot('calendar.snapshot'),
            related_name='history',
            model_name='RuleHistory',
            app_label='occasions'
        )
        class RuleProxy(schedule_rule_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('calendar.snapshot'),
            related_name='history',
            model_name='CalendarHistory',
            app_label='occasions'
        )
        class CalendarProxy(schedule_calendar_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('calendarrelation.snapshot'),
            related_name='history',
            model_name='CalendarRelationHistory',
            app_label='occasions',
        )
        class CalendarRelationProxy(schedule_calendarrelation_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('event.snapshot'),
            related_name='history',
            model_name='EventHistory',
            app_label='occasions'
        )
        class EventProxy(schedule_event_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('eventrelation.snapshot'),
            related_name='history',
            model_name='EventRelationHistory',
            app_label='occasions',
        )
        class EventRelationProxy(schedule_eventrelation_model):
            class Meta:
                proxy = True
