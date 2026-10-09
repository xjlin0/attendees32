"""``/persons/api/datagrid_data_familyattendees/`` against the golden congregation."""

import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from attendees.persons.models import FolkAttendee
from attendees.tests.golden.constants import FolkCategory
from attendees.tests.golden.constants import Relations
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestDatagridDataFamilyattendees:
    def test_family_membership_rows_carry_the_role(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.get(
            "/persons/api/datagrid_data_familyattendees/",
            {"categoryId": FolkCategory.FAMILY},
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert {row["attendee"] for row in rows} >= {
            str(golden.attendee("chen_zhiming").id),
            str(golden.attendee("chen_joshua").id),
        }
        assert {row["role"] for row in rows} >= {Relations.HUSBAND, Relations.SON}
        assert any(
            row["folk"]["display_name"].startswith("陳志明家") for row in rows
        )

    def test_the_listing_reads_the_folks_in_one_query(self, golden, api_login):
        """Every row nests its folk; the queryset select_relates it rather than
        fetching one folk per membership."""
        grace = golden.attendee("chen_grace")
        client = target(api_login("golden_data_organizer"), grace)
        with CaptureQueriesContext(connection) as queries:
            response = client.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY})
        assert response.status_code == 200
        assert len(response.json()["data"]) >= 6
        # The list and its count query may each subselect folks; what must not
        # appear is a folk fetched by id for every row.
        per_row = [
            q["sql"] for q in queries.captured_queries
            if 'FROM "persons_folks"' in q["sql"] and '"persons_folks"."id" = ' in q["sql"]
        ]
        assert per_row == []

    def test_a_token_authenticated_client_is_served(self, golden, token_client):
        client = target(token_client("golden_data_organizer"), golden.attendee("chen_grace"))
        response = client.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY})
        assert response.status_code == 200, response.content

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY})
        assert response.status_code == 403

    def test_the_spy_guard_holds_for_a_token_client(self, golden, token_client):
        """A token client is held to the same rules as a session: an ordinary
        member may not reach a stranger's record, and a deleted attendee is a 404."""
        stranger = target(token_client("golden_crossing_member"), golden.attendee("chen_grace"))
        assert stranger.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY}).status_code == 403

        deleted = target(token_client("golden_data_organizer"), golden.attendee("peng_jinlong"))
        assert deleted.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY}).status_code == 404

    def test_a_member_is_added_to_a_family_by_folk_id(self, golden, api_login):
        """A write names the folk by id and reads it back nested, the shape the
        family grid and API clients both use."""
        grace = golden.attendee("chen_grace")
        kevin = golden.attendee("xu_kevin")
        family = golden.folk("HH_CHEN_THREE_GEN")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.post(
            "/persons/api/datagrid_data_familyattendees/",
            {"folk": str(family.id), "attendee": str(kevin.id), "role": Relations.FRIEND, "infos": {}},
            format="json",
        )
        assert response.status_code == 201, response.content
        row = response.json()
        assert row["folk"]["id"] == str(family.id)
        assert row["folk"]["display_name"].startswith("陳志明家")
        assert FolkAttendee.objects.filter(folk=family, attendee=kevin, role=Relations.FRIEND).exists()

    def test_the_family_grid_posts_a_multipart_row(self, golden, api_login):
        """The attendee page submits FormData: folk=<id>, infos as a JSON string."""
        grace = golden.attendee("chen_grace")
        kevin = golden.attendee("xu_kevin")
        family = golden.folk("HH_CHEN_THREE_GEN")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.post(
            "/persons/api/datagrid_data_familyattendees/",
            {
                "folk": str(family.id),
                "attendee": str(kevin.id),
                "role": Relations.FRIEND,
                "display_order": 9,
                "infos": json.dumps({"show_secret": {}, "updating_attendees": {}, "comment": None, "body": None}),
            },
            format="multipart",
        )
        assert response.status_code == 201, response.content
        assert response.json()["folk"]["category"] == FolkCategory.FAMILY

    def test_a_membership_is_moved_by_patching_the_folk_id(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        kevin = golden.attendee("xu_kevin")
        chens = golden.folk("HH_CHEN_THREE_GEN")
        membership = FolkAttendee.objects.get(attendee=kevin, folk__category=FolkCategory.FAMILY)
        client = target(api_login("golden_data_organizer"), kevin)
        response = client.patch(
            f"/persons/api/datagrid_data_familyattendees/{membership.id}/",
            {"folk": str(chens.id), "role": Relations.FRIEND},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["folk"]["id"] == str(chens.id)
        membership.refresh_from_db()
        assert membership.folk == chens
        assert membership.role_id == Relations.FRIEND
        assert grace.folks.filter(pk=chens.pk).exists()  # the family itself is untouched

    def test_a_second_row_for_the_same_pair_is_refused(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        family = golden.folk("HH_CHEN_THREE_GEN")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.post(
            "/persons/api/datagrid_data_familyattendees/",
            {"folk": str(family.id), "attendee": str(grace.id), "role": Relations.DAUGHTER, "infos": {}},
            format="json",
        )
        assert response.status_code == 400
        assert "non_field_errors" in response.json()
