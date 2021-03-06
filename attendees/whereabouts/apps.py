import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps


class WhereaboutsConfig(AppConfig):
    name = "attendees.whereabouts"

    def ready(self):
        address_country_model = django_apps.get_model("address.Country", require_ready=False)
        address_state_model = django_apps.get_model("address.State", require_ready=False)
        address_locality_model = django_apps.get_model("address.Locality", require_ready=False)
        address_address_model = django_apps.get_model("address.Address", require_ready=False)

        pghistory.track(
            pghistory.Snapshot('country.snapshot'),
            related_name='history',
            model_name='CountryHistory',
            app_label='whereabouts'
        )(address_country_model)

        pghistory.track(
            pghistory.Snapshot('state.snapshot'),
            related_name='history',
            model_name='StateHistory',
            app_label='whereabouts'
        )(address_state_model)

        pghistory.track(
            pghistory.Snapshot('locality.snapshot'),
            related_name='history',
            model_name='LocalityHistory',
            app_label='whereabouts'
        )(address_locality_model)

        pghistory.track(
            pghistory.Snapshot('address.snapshot'),
            related_name='history',
            model_name='AddressHistory',
            app_label='whereabouts'
        )(address_address_model)
