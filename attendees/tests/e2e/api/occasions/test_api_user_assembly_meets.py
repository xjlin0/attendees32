"""``/occasions/api/user_assembly_meets/`` against the golden congregation."""

import pytest

from attendees.occasions.models import Assembly
from attendees.occasions.models import Meet
from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestUserAssemblyMeets:
    def test_meets_can_be_scoped_to_an_assembly(self, golden, api_login):
        junior = Assembly.objects.get(slug=AssemblySlugs.JUNIOR_REGULAR)
        client = api_login("golden_data_organizer")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_joshua").id)
        )
        response = client.get(
            "/occasions/api/user_assembly_meets/",
            {"assemblies[]": junior.pk, "take": 100},
        )
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert {MeetSlugs.THE_ROCK, MeetSlugs.LITTLE_FOOT} <= slugs

    def test_the_target_attendees_own_meets_lead_the_first_page(
        self, golden, api_login
    ):
        """The attendee page's participation grid resolves meet names from
        the first page of this endpoint only, so the attendee's own meets
        must sort ahead of everyone else's -- or her rows show blank."""
        grace = golden.attendee("chen_grace")
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(grace.id))
        response = client.get(
            "/occasions/api/user_assembly_meets/",
            {"searchOperation": "contains", "searchValue": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["totalCount"] > len(body["data"])  # it really is paged
        joined = set(
            Meet.objects.filter(attendingmeet__attending__attendee=grace).values_list(
                "slug", flat=True
            )
        )
        first_page = [row["slug"] for row in body["data"]]
        assert joined <= set(first_page)
        assert all(slug in joined for slug in first_page[: len(joined)])
