"""The attendee_update page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendeeUpdate:
    def test_a_member_may_read_their_own_record(self, golden, login):
        client = login("golden_member")
        attendee = golden.attendee("chen_zhiming")
        assert client.get(f"/persons/attendee/{attendee.id}").status_code == 200

    def test_a_parent_may_read_a_child_they_schedule(self, golden, login):
        client = login("golden_member")
        joshua = golden.attendee("chen_joshua")
        assert client.get(f"/persons/attendee/{joshua.id}").status_code == 200

    def test_a_parent_may_not_read_an_unrelated_child(self, golden, login):
        client = login("golden_member")
        stranger = golden.attendee("lee_peter")
        assert client.get(f"/persons/attendee/{stranger.id}").status_code == 403

    def test_a_guardian_may_read_their_ward(self, golden, login):
        """Kevin's guardians are not his parents, but they do schedule him."""
        client = login("golden_counselor")  # xu_jianguo
        kevin = golden.attendee("xu_kevin")
        assert client.get(f"/persons/attendee/{kevin.id}").status_code == 200

    def test_a_coworker_group_may_read_anyone_in_the_organization(self, golden, login):
        client = login("golden_children_organizer")
        for key in ("wang_yulan", "tsai_serena", "guo_mingzhu"):
            attendee = golden.attendee(key)
            assert client.get(f"/persons/attendee/{attendee.id}").status_code == 200

    def test_a_login_with_no_attendee_may_read_nobody(self, golden, login):
        client = login("golden_unaffiliated")
        attendee = golden.attendee("chen_grace")
        assert client.get(f"/persons/attendee/{attendee.id}").status_code == 403

    def test_the_update_page_offers_the_organization_pasts(self, golden, login):
        client = login("golden_data_organizer")
        response = client.get(f"/persons/attendee/{golden.attendee('chen_grace').id}")
        assert response.status_code == 200
        assert response.context["show_create_attendee"] is True
        # organization.infos.settings.past_category_to_attendingmeet_meet
        assert "已受洗 baptized" in response.context["pasts_to_add"]
        assert response.context["family_category_id"] == 0
