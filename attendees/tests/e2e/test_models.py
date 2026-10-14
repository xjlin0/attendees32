"""Model and data checks on the golden congregation that go through no endpoint."""

import pytest
from django.contrib.contenttypes.models import ContentType

from attendees.occasions.models import Assembly
from attendees.occasions.models import Price
from attendees.persons.models import Attendee
from attendees.persons.models import Registration
from attendees.tests.e2e.helpers import retreat_assembly

pytestmark = pytest.mark.django_db


class TestModels:
    def test_the_same_person_cannot_register_twice_for_one_assembly(
        self, golden
    ):
        """The database says so, and it is the constraint that keeps the
        headcount honest when a form is submitted twice."""
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

    def test_another_organizations_attendee_is_invisible(self, golden, api_login):
        """The seed carries 天堂 Heaven as a second organization."""
        heaven_attendee = Attendee.all_objects.filter(
            division__organization__slug="faBd6C_heaven"
        ).first()
        assert heaven_attendee is None, (
            "the golden dataset replaces the seed's demo people; "
            "the second organization is vocabulary only"
        )

    def test_under_same_org_with_is_true_within_the_church(self, golden):
        zhiming = golden.attendee("chen_zhiming")
        assert zhiming.under_same_org_with(str(golden.attendee("wong_wilson").id))
        assert not zhiming.under_same_org_with(str(zhiming.id).replace("0", "1"))
