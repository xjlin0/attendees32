import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps


class WhereaboutsConfig(AppConfig):
    name = "attendees.whereabouts"

    def ready(self):
        address_country_model = django_apps.get_model("address.Country", require_ready=False)

        pghistory.track(
            pghistory.Snapshot('country.snapshot'),
            related_name='history',
            model_name='CountryHistory',
            app_label='whereabouts'
        )(address_country_model)
