"""``/persons/api/all_registrations/`` against the golden congregation."""

import pytest

from attendees.persons.models import Registration
from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.e2e.helpers import REGISTRATIONS, retreat_assembly

pytestmark = pytest.mark.django_db


class TestAllRegistrations:
    def test_registrations_are_listed_for_the_retreat(self, golden, api_login):
        from attendees.occasions.models import Assembly

        assembly = Assembly.objects.get(slug=AssemblySlugs.SUMMER_RETREAT)
        registration = golden.registrations["HH_CHEN_THREE_GEN"]
        client = api_login("golden_conference_organizer")
        response = client.get(
            "/persons/api/all_registrations/",
            {"assembly": assembly.pk, "registrant": str(registration.registrant_id)},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] == 1
        assert response.json()["data"][0]["infos"]["apply_key"]

        by_id = client.get(f"/persons/api/all_registrations/{registration.pk}/")
        assert by_id.status_code == 200
        assert by_id.json()["id"] == registration.pk

    def test_the_retreat_registrations_are_listed_for_the_assembly(
        self, golden, api_login
    ):
        client = api_login("golden_conference_organizer")
        retreat = retreat_assembly()
        response = client.get(REGISTRATIONS, {"assembly": retreat.id})
        assert response.status_code == 200
        assert response.json()

    def test_a_household_can_be_registered_and_carries_what_was_paid(
        self, golden, api_login
    ):
        """A registration is the row a treasurer reconciles against.

        The amounts live in ``infos`` rather than columns, so a write that
        dropped them would still look like a successful registration until
        somebody tried to work out who had paid.
        """
        client = api_login("golden_conference_organizer")
        retreat = retreat_assembly()
        newcomer = golden.attendee("feng_ruian")
        assert not Registration.objects.filter(
            assembly=retreat, registrant=newcomer
        ).exists()

        response = client.post(
            REGISTRATIONS,
            {
                "assembly": retreat.id,
                "registrant": str(newcomer.id),
                "infos": {
                    "price": "150.75",
                    "donation": "85.00",
                    "credit": "35.50",
                    "apply_type": "online",
                    "apply_key": "e2e-001",
                },
            },
            format="json",
        )
        assert response.status_code == 201, response.content

        written = Registration.objects.get(assembly=retreat, registrant=newcomer)
        assert written.infos["price"] == "150.75"
        assert written.infos["donation"] == "85.00"
        assert written.infos["apply_type"] == "online"

    def test_an_anonymous_caller_cannot_read_registrations(self, golden, client):
        response = client.get(REGISTRATIONS)
        assert response.status_code in {302, 403}
