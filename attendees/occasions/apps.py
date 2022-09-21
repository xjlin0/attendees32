import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps


class OccasionsConfig(AppConfig):
    name = "attendees.occasions"

    def ready(self):
        celery_task_model = django_apps.get_model("django_celery_beat.PeriodicTask", require_ready=False)
        celery_crontab_model = django_apps.get_model("django_celery_beat.CrontabSchedule", require_ready=False)
        celery_interval_model = django_apps.get_model("django_celery_beat.IntervalSchedule", require_ready=False)
        schedule_calendar_model = django_apps.get_model("schedule.Calendar", require_ready=False)
        schedule_calendarrelation_model = django_apps.get_model("schedule.CalendarRelation", require_ready=False)
        schedule_event_model = django_apps.get_model("schedule.Event", require_ready=False)
        schedule_eventrelation_model = django_apps.get_model("schedule.EventRelation", require_ready=False)
        schedule_rule_model = django_apps.get_model("schedule.Rule", require_ready=False)
        schedule_occurrence_model = django_apps.get_model("schedule.Occurrence", require_ready=False)

        @pghistory.track(
            pghistory.Snapshot('intervalschedule.snapshot'),
            related_name='history',
            model_name='IntervalScheduleHistory',
            app_label='occasions'
        )
        class IntervalScheduleProxy(celery_interval_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('crontabschedule.snapshot'),
            related_name='history',
            model_name='CrontabScheduleHistory',
            app_label='occasions'
        )
        class CrontabScheduleProxy(celery_crontab_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('periodictask.snapshot'),
            related_name='history',
            model_name='PeriodicTaskHistory',
            app_label='occasions'
        )
        class PeriodicTaskProxy(celery_task_model):
            class Meta:
                proxy = True

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

        @pghistory.track(
            pghistory.Snapshot('occurrence.snapshot'),
            related_name='history',
            model_name='OccurrenceHistory',
            app_label='occasions',
        )
        class OccurrenceProxy(schedule_occurrence_model):
            class Meta:
                proxy = True
