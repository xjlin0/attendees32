"""``/whereabouts/api/datagrid_data_place/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestDatagridDataPlace:
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
