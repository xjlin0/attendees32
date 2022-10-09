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

        @pghistory.track(
            pghistory.Snapshot('country.snapshot'),
            pghistory.BeforeDelete('country.before_delete'),
            related_name='history',
            model_name='CountryHistory',
            app_label='whereabouts'
        )
        class CountryProxy(address_country_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('state.snapshot'),
            pghistory.BeforeDelete('state.before_delete'),
            related_name='history',
            model_name='StateHistory',
            app_label='whereabouts'
        )
        class StateProxy(address_state_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('locality.snapshot'),
            pghistory.BeforeDelete('locality.before_delete'),
            related_name='history',
            model_name='LocalityHistory',
            app_label='whereabouts'
        )
        class LocalityProxy(address_locality_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('address.snapshot'),
            pghistory.BeforeDelete('address.before_delete'),
            related_name='history',
            model_name='AddressHistory',
            app_label='whereabouts'
        )
        class AddressProxy(address_address_model):
            class Meta:
                proxy = True
