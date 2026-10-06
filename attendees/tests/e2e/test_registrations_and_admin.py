"""Two surfaces nothing else in the suite reaches.

Registrations are the money side of a retreat — a price, a donation, a credit
and how the person applied — and the golden dataset seeds them, but until now
only ever *read* them back.  A retreat that cannot take a new registration is
not much of a retreat.

The admin is the other one.  It is where somebody goes to fix what the ordinary
screens cannot, and django-pghistory hangs the "who changed this, and when"
pages off it.  Neither has ever been opened by a test, so neither has ever
proved it is reachable by the right person and shut to everybody else.
"""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from attendees.occasions.models import Assembly, Price
from attendees.persons.models import Attendee, Registration

pytestmark = pytest.mark.django_db

REGISTRATIONS = "/persons/api/all_registrations/"


def retreat_assembly() -> Assembly:
    return Assembly.objects.get(slug="cfcch_summer_retreat_2025")


# ------------------------------------------------------------- registrations
class TestRetreatRegistration:
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

    def test_the_same_person_cannot_register_twice_for_one_assembly(
        self, golden, api_login
    ):
        """The database says so, and it is the constraint that keeps the
        headcount honest when a form is submitted twice."""
        client = api_login("golden_conference_organizer")
        retreat = retreat_assembly()
        already = Registration.objects.filter(assembly=retreat).first()

        from django.db import IntegrityError, transaction

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Registration.objects.create(
                    assembly=retreat, registrant=already.registrant
                )

    def test_the_retreat_prices_are_readable_and_bounded(self, golden):
        prices = Price.objects.filter(assembly=retreat_assembly())
        assert prices.count() >= 2
        for price in prices:
            assert price.price_value >= 0
            assert price.start < price.finish

    def test_an_anonymous_caller_cannot_read_registrations(self, golden, client):
        response = client.get(REGISTRATIONS)
        assert response.status_code in {302, 403}


# --------------------------------------------------------------------- admin
class TestAdminAndHistory:
    def test_a_superuser_reaches_the_admin_index(self, golden, login):
        client = login("golden_superuser")
        response = client.get("/admin123/")
        assert response.status_code == 200
        assert b"Attendees" in response.content or b"attendees" in response.content

    def test_an_ordinary_member_is_turned_away_from_the_admin(self, golden, login):
        client = login("golden_member")
        response = client.get("/admin123/", follow=False)
        # Django's admin sends a non-staff user to its own login page.
        assert response.status_code in {302, 403}
        if response.status_code == 302:
            assert "login" in response["Location"]

    def test_the_attendee_changelist_opens_and_finds_a_person(self, golden, login):
        client = login("golden_superuser")
        response = client.get("/admin123/persons/attendee/", {"q": "Zhiming"})
        assert response.status_code == 200
        assert b"Zhiming" in response.content

    def test_a_change_is_recorded_in_the_history_the_admin_exposes(self, golden, login):
        """pghistory is what answers "who changed this?" months later.

        The trigger fires in the database, so this writes through the ORM and
        then reads the event table the admin's history page is built on.
        """
        attendee = golden.attendee("feng_ruian")
        before = attendee.history.count()

        attendee.first_name2 = "瑞安改"
        attendee.save()

        assert attendee.history.count() > before
        latest = attendee.history.order_by("-pgh_created_at").first()
        assert latest.first_name2 == "瑞安改"

        attendee.first_name2 = "瑞安"
        attendee.save()

    def test_every_registered_model_has_a_content_type(self, golden):
        """`update_content_types` underpins the generic relations that notes
        and places hang off, so a missing row breaks them silently."""
        for model in (Attendee, Registration, Assembly):
            assert ContentType.objects.get_for_model(model).pk

    def test_the_admin_url_is_not_the_default_one(self, golden):
        """A guessable admin path is a free door to rattle."""
        assert reverse("admin:index") != "/admin/"
