"""Every ``/whereabouts/api/…`` endpoint: where the church and its people are."""

import pytest

from attendees.tests.golden.constants import DIVISION_SLUGS, ORGANIZATION_ID

pytestmark = pytest.mark.django_db


class TestOrganizationalGeography:
    def test_the_users_organization_is_returned(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get("/whereabouts/api/user_organizations/")
        assert response.status_code == 200
        rows = response.json()["data"]
        assert [row["id"] for row in rows] == [ORGANIZATION_ID]
        assert rows[0]["infos"]["acronym"] == "CFCCH"

    def test_all_four_divisions_are_listed(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/user_divisions/", {"take": 50})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert {
            DIVISION_SLUGS[1], DIVISION_SLUGS[2], DIVISION_SLUGS[3], DIVISION_SLUGS[5]
        } <= slugs

    def test_a_single_division_can_be_fetched(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/user_divisions/", {"division_id": 3})
        assert response.status_code == 200
        assert [row["slug"] for row in response.json()["data"]] == [DIVISION_SLUGS[3]]

    def test_campuses_properties_suites_and_rooms(self, golden, api_login):
        client = api_login("golden_data_organizer")
        for endpoint, expected in (
            ("organizational_campuses", "CFCCH Main"),
            ("organizational_properties", "CFCCH Fellowship Hall"),
            ("organizational_suites", "CFCCH Zoom"),
            ("organizational_rooms", "CFCCH Zoom 3583017026"),
        ):
            response = client.get(f"/whereabouts/api/{endpoint}/", {"take": 100})
            assert response.status_code == 200, endpoint
            names = {row["display_name"] for row in response.json()["data"]}
            assert expected in names, endpoint

    def test_rooms_can_be_searched(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/organizational_rooms/", {"searchValue": "Zoom"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_location_content_types_are_listed_for_the_site_picker(
        self, golden, api_login
    ):
        """The extra ``genres``/``display_order`` columns, filled in by
        ``manage.py update_content_types`` and read back by raw SQL."""
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/content_type_models/", {"query": "location"}
        )
        assert response.status_code == 200
        models = {row["model"] for row in response.json()["data"]}
        assert {"room", "suite", "property", "campus"} <= models


class TestAddresses:
    def test_the_golden_households_produced_real_addresses(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/all_addresses/", {"take": 10})
        assert response.status_code == 200
        assert response.json()["totalCount"] > 100

    def test_addresses_can_be_searched_by_street(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/all_addresses/", {"searchValue": "Tennyson"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_states_are_available_for_the_address_form(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/all_states/", {"searchValue": "Calif"})
        assert response.status_code == 200
        assert "California" in {row["name"] for row in response.json()["data"]}

    def test_a_familys_place_is_fetched_by_id(self, golden, api_login):
        zhiming = golden.attendee("chen_zhiming")
        place = golden.folk("HH_CHEN_THREE_GEN").places.first()
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(zhiming.id))
        response = client.get(f"/whereabouts/api/datagrid_data_place/{place.id}/")
        assert response.status_code == 200
        payload = response.json()
        assert payload["display_name"] == "main"
        assert payload["address"]["city"]
        assert payload["address"]["postal_code"]
        assert payload["street"]

    def test_a_personal_address_sits_alongside_the_family_one(self, golden, api_login):
        esther = golden.attendee("zhang_esther")  # away at college
        assert esther.places.count() == 1
        personal = esther.places.first()
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(esther.id))
        response = client.get(f"/whereabouts/api/datagrid_data_place/{personal.id}/")
        assert response.status_code == 200
        assert response.json()["display_name"] == "resident"
        # and the family she belongs to still has its own address
        assert golden.folk("HH_ZHANG_PASTOR").places.count() == 1

    def test_an_address_can_be_relabelled(self, golden, api_login):
        """The round trip the address grid does: read a row, send it back."""
        esther = golden.attendee("zhang_esther")
        place = esther.places.first()
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(esther.id))
        payload = client.get(
            f"/whereabouts/api/datagrid_data_place/{place.id}/"
        ).json()
        payload["display_name"] = "dorm"

        response = client.put(
            f"/whereabouts/api/datagrid_data_place/{place.id}/", payload, format="json"
        )
        assert response.status_code == 200, response.content
        place.refresh_from_db()
        assert place.display_name == "dorm"

    def test_an_ordinary_member_cannot_relabel_someone_elses_address(
        self, golden, api_login
    ):
        esther = golden.attendee("zhang_esther")
        place = esther.places.first()
        admin = api_login("golden_data_organizer")
        admin.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(esther.id))
        payload = admin.get(f"/whereabouts/api/datagrid_data_place/{place.id}/").json()
        payload["display_name"] = "hacked"

        client = api_login("golden_crossing_member")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(esther.id))
        response = client.put(
            f"/whereabouts/api/datagrid_data_place/{place.id}/", payload, format="json"
        )
        assert response.status_code == 403
        place.refresh_from_db()
        assert place.display_name != "hacked"

    def test_places_are_searchable_by_a_privileged_user(self, golden, api_login):
        """``user_places`` only serves privileged logins; the ordinary-member
        branch reaches for an attribute Attendee does not have."""
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/user_places/", {"searchValue": "Tennyson"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1
