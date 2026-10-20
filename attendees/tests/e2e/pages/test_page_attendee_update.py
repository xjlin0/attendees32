"""The attendee_update page against the golden congregation."""

import pytest

from attendees.persons.models import Attendee
from attendees.persons.services import AttendeeMergeService

pytestmark = pytest.mark.django_db


def _ava(golden):
    division = golden.attendee("chen_grace").division
    return Attendee.objects.create(first_name="Ava", last_name="Chen", division=division, gender="unspecified")


def _twins(golden):
    return _ava(golden), _ava(golden)


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

    def test_a_link_to_a_merged_away_record_opens_the_one_that_holds_it(self, golden, login):
        primary, duplicate = _twins(golden)
        AttendeeMergeService.merge(duplicate, primary)
        client = login("golden_data_organizer")

        response = client.get(f"/persons/attendee/{duplicate.id}")

        assert response.status_code == 302
        assert response.url == f"/persons/attendee/{primary.id}?merged_from={duplicate.id}"

    def test_the_merged_record_says_who_was_merged_in(self, golden, login):
        primary, duplicate = _twins(golden)
        AttendeeMergeService.merge(duplicate, primary, by=str(golden.attendee("chen_grace").id))
        client = login("golden_data_organizer")

        response = client.get(f"/persons/attendee/{primary.id}?merged_from={duplicate.id}")

        assert response.status_code == 200
        [record] = response.context["merged_from"]
        assert record["id"] == str(duplicate.id)
        assert record["followed"] is True
        assert response.context["can_merge"] is True
        html = response.content.decode()
        assert "You followed a link to a record that was merged into this one" in html
        assert "Ava Chen" in html
        assert "merged ×1" in html
        assert "Undo merge" in html
        assert "Merge with another record" in html

    def test_a_member_gets_no_merge_controls(self, golden, login):
        client = login("golden_member")

        response = client.get(f"/persons/attendee/{golden.attendee('chen_zhiming').id}")

        assert response.status_code == 200
        assert response.context["can_merge"] is False
        assert response.context["merged_from"] == []
        assert "Merge with another record" not in response.content.decode()

    def test_a_member_sees_no_merges(self, golden, login):
        member = golden.attendee("chen_zhiming")
        duplicate = _ava(golden)
        AttendeeMergeService.merge(duplicate, member)
        client = login("golden_member")

        response = client.get(f"/persons/attendee/{member.id}?merged_from={duplicate.id}")

        assert response.status_code == 200
        assert response.context["merged_from"] == []
        html = response.content.decode()
        assert "merged ×" not in html
        assert "You followed a link" not in html

    def test_the_new_person_page_carries_no_merges(self, golden, login):
        # A deleted record that was never merged is not a merge into "new".
        _ava(golden).delete()
        client = login("golden_data_organizer")

        response = client.get("/persons/attendee/new")

        assert response.status_code == 200
        assert response.context["merged_from"] == []
        assert "merged ×" not in response.content.decode()

    def test_the_chip_counts_the_merges_and_the_list_says_what_each_brought(self, golden, login):
        primary, first = _twins(golden)
        second = _ava(golden)
        second.infos["contacts"] = {"phone1": "+15105550199"}
        second.save()
        AttendeeMergeService.merge(first, primary)
        AttendeeMergeService.merge(second, primary)
        client = login("golden_data_organizer")

        response = client.get(f"/persons/attendee/{primary.id}")

        html = response.content.decode()
        assert "merged ×2" in html
        # No link was followed, so no notice; the list has one Undo per merge.
        assert "You followed a link" not in html
        assert html.count("Undo merge") == 2
        merges = {record["id"]: record for record in response.context["merged_from"]}
        assert set(merges) == {str(first.id), str(second.id)}
        assert merges[str(second.id)]["made"] == second.created.date()
        assert merges[str(second.id)]["contact"] == "+15105550199"
        assert merges[str(second.id)]["brought"] == ""  # a plain twin brings nothing else
        assert f"a record made {second.created:%Y-%m-%d} with +15105550199, merged on" in html
        assert "It brought nothing else." in html
