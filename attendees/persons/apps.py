from django.apps import AppConfig


class PersonsConfig(AppConfig):
    name = "attendees.persons"

    def ready(self):
        # importing signal handlers # https://docs.djangoproject.com/en/dev/topics/signals/#preventing-duplicate-signals
        import attendees.persons.signals
