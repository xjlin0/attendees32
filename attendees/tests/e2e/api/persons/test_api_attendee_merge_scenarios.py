"""Merging records that carry every kind of data, several times over, through
the API: preview, merge, the picks as an edit, and one undo."""

from datetime import date, timedelta

import pytest
from address.models import Address
from django.contrib.contenttypes.models import ContentType

from attendees.occasions.models import Attendance
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Category,
    Folk,
    FolkAttendee,
    Note,
    Past,
    Registration,
    Relation,
)
from attendees.tests.e2e.helpers import target
from attendees.tests.golden.constants import AttendanceCategory, Relations
from attendees.users.models import User
from attendees.whereabouts.models import Place

pytestmark = pytest.mark.django_db

API = "/persons/api/datagrid_data_attendee/"


def _preview(client, one, other):
    return client.get(f"{API}merge_preview/", {"a": str(one.id), "b": str(other.id)})


def _merge(client, duplicate, primary):
    return client.post(f"{API}{duplicate.id}/merge/", {"primary": str(primary.id)}, format="json")


def _unmerge(client, duplicate):
    return client.post(f"{API}{duplicate.id}/unmerge/")


def _fresh(attendee):
    return Attendee.all_objects.get(pk=attendee.pk)


class Records:
    """Three records of one person in the golden congregation, each with its own
    data: the oldest (Sam) is the primary, the middle one (Samuel) carries a bit
    of everything, the newest (Sammy) is sparse."""

    def __init__(self, golden):
        self.golden = golden
        self.meet = golden.meets["youth_group"]
        self.sunday_school = golden.meets["youth_sunday_school"]
        self.character = golden.characters["youth_student"]
        self.division = self.meet.assembly.division
        self.organization = self.division.organization
        self.attendee_type = ContentType.objects.get_for_model(Attendee)
        self.scheduled = Category.objects.get(pk=AttendanceCategory.SCHEDULED)
        self.gatherings = sorted(
            (g for g in golden.gatherings if g.meet_id == self.meet.id), key=lambda g: g.start
        )[:2]
        assert len(self.gatherings) == 2, "the youth group needs two gatherings"

        self.parent = self._attendee("Peter", "Tsai")
        self.child = self._attendee("Penny", "Tsai")
        self.family = self._folk(0, "Tsai household")
        self._member(self.family, self.parent, Relations.FATHER)
        self.friends = self._folk(Attendee.NON_FAMILY_CATEGORY, "Peter's friends")
        self._member(self.friends, self.parent, Relations.HIDDEN)

        self.sam = self._attendee(
            "Sam", "Tsai", actual_birthday=date(2008, 6, 22), gender="MALE",
            photo="attendee_portrait/sam.jpg",
            infos={"fixed": {"grade": 17, "insurer": "Kaiser"},
                   "contacts": {"phone1": "+15105550107", "email1": "sam@example.org", "WeChat1": "sam_t"}},
        )
        self._member(self.family, self.sam, Relations.SON)
        self._enroll(self.sam, self.meet)
        self._check_in(self.sam, self.gatherings[0])
        self.shared_address = Address.objects.create(raw="1 Main St, Hayward, CA")
        self._place(self.sam, self.shared_address, "home")
        self._note(self.sam, "likes basketball")
        self._past(self.sam, "baptized")

        self.samuel = self._attendee(
            "Samuel", "Tsai", actual_birthday=date(2008, 6, 23), gender="MALE",
            photo="attendee_portrait/samuel.jpg",
            infos={"fixed": {"grade": 16, "food_pref": "peanut allergy", "insurer": "Blue Shield"},
                   "contacts": {"phone1": "+15105550199", "phone2": "+15105550107",
                                "email1": "sam2@example.org", "wechat": "sam_t", "line1": "samtsai"},
                   "schedulers": {str(self.parent.id): True}},
        )
        self.login = User.objects.create(username="samuel-tsai-login", email="samuel@example.org")
        Attendee.objects.filter(pk=self.samuel.pk).update(user=self.login)
        self._member(self.family, self.samuel, Relations.SON)  # the same family as Sam
        self.second_family = self._folk(0, "Tsai household 2")
        self._member(self.second_family, self.samuel, Relations.SON)
        self._member(self.friends, self.samuel, Relations.FRIEND)
        self._enroll(self.samuel, self.meet)  # the same group as Sam
        self._check_in(self.samuel, self.gatherings[0])  # the same check-in as Sam
        self._check_in(self.samuel, self.gatherings[1])
        self._place(self.samuel, self.shared_address, "home")  # the same address as Sam
        self._place(self.samuel, Address.objects.create(raw="2 Oak Ave, Hayward, CA"), "grandma")
        self._note(self.samuel, "allergic to peanuts")
        self._past(self.samuel, "believer")
        self.registration = Registration.objects.create(registrant=self.samuel, assembly=self.meet.assembly)
        Attending.objects.create(attendee=self.samuel, registration=self.registration)
        self.child.infos["emergency_contacts"] = {str(self.samuel.id): True}
        self.child.save()

        self.sammy = self._attendee(
            "Sammy", "Tsai", gender="MALE",
            infos={"fixed": {"mobility": 1}, "contacts": {"phone1": "+15105550300"}},
        )
        self._enroll(self.sammy, self.sunday_school)
        self._note(self.sammy, "new this year")

        # Oldest first, whatever the clock says.
        for days, attendee in ((3, self.sam), (2, self.samuel), (1, self.sammy)):
            Attendee.objects.filter(pk=attendee.pk).update(created=attendee.created - timedelta(days=days))

    def _attendee(self, first_name, last_name, infos=None, **fields):
        attendee = Attendee.objects.create(
            first_name=first_name, last_name=last_name, division=self.division,
            gender=fields.pop("gender", "unspecified"), **fields,
        )
        if infos:
            attendee.infos.update(infos)
            attendee.save()
        return attendee

    def _folk(self, category_id, display_name):
        return Folk.objects.create(category_id=category_id, division=self.division, display_name=display_name)

    def _member(self, folk, attendee, role_id):
        return FolkAttendee.objects.create(folk=folk, attendee=attendee, role=Relation.objects.get(pk=role_id))

    def _enroll(self, attendee, meet):
        return AttendingMeet.objects.create(
            attending=attendee.attendings.get(), meet=meet, character=self.character,
            category=self.scheduled, start=meet.start, finish=meet.finish,
        )

    def _check_in(self, attendee, gathering):
        return Attendance.objects.create(
            gathering=gathering, attending=attendee.attendings.get(), character=self.character,
            start=gathering.start, finish=gathering.finish,
        )

    def _linked(self, model, attendee, **fields):
        return model.objects.create(
            content_type=self.attendee_type, object_id=str(attendee.id), organization=self.organization, **fields,
        )

    def _place(self, attendee, address, display_name):
        return self._linked(Place, attendee, address=address, display_name=display_name)

    def _note(self, attendee, body):
        return self._linked(Note, attendee, category=Note.objects.first().category, body=body)

    def _past(self, attendee, display_name):
        return self._linked(Past, attendee, category=Past.objects.first().category, display_name=display_name)

    # What a record holds now, live rows only.
    def enrollments(self, attendee):
        return sorted(AttendingMeet.objects.filter(attending__attendee=attendee, attending__is_removed=False).values_list("meet__display_name", flat=True))

    def check_ins(self, attendee):
        return sorted(Attendance.objects.filter(attending__attendee=attendee, attending__is_removed=False).values_list("gathering__start", flat=True))

    def folks(self, attendee):
        return sorted(FolkAttendee.objects.filter(attendee=attendee).exclude(role_id=Relations.HIDDEN).values_list("folk__display_name", flat=True))

    def places(self, attendee):
        return sorted(Place.objects.filter(content_type=self.attendee_type, object_id=str(attendee.id)).values_list("display_name", flat=True))

    def linked(self, model, attendee):
        return model.objects.filter(content_type=self.attendee_type, object_id=str(attendee.id)).count()


class TestMergingRecordsThatCarryEverything:
    def test_two_merges_with_picks_and_one_undo(self, golden, token_client):
        r = Records(golden)
        client = token_client("golden_data_organizer")

        # The preview shows the merge before it happens: the older record is the primary.
        preview = _preview(client, r.samuel, r.sam)
        assert preview.status_code == 200, preview.content
        body = preview.json()
        assert body["primary"]["id"] == str(r.sam.id) and body["duplicate"]["name"] == "Samuel Tsai"
        assert body["details"]["actual_birthday"] == {"primary": "2008-06-22", "duplicate": "2008-06-23"}
        assert body["details"]["first_name"] == {"primary": "Sam", "duplicate": "Samuel"}
        assert body["details"]["fixed.grade"] == {"primary": 17, "duplicate": 16}
        assert body["details"]["fixed.insurer"] == {"primary": "Kaiser", "duplicate": "Blue Shield"}
        assert body["details"]["fixed.food_pref"] == {"primary": None, "duplicate": "peanut allergy"}
        assert body["details"]["photo"] == {"primary": "attendee_portrait/sam.jpg", "duplicate": "attendee_portrait/samuel.jpg"}
        assert body["contacts"] == {
            "phone1": {"value": "+15105550107", "from": "primary"},
            "phone2": {"value": "+15105550199", "from": "duplicate"},
            "email1": {"value": "sam@example.org", "from": "primary"},
            "email2": {"value": "sam2@example.org", "from": "duplicate"},
            "wechat1": {"value": "sam_t", "from": "primary"},
            "line1": {"value": "samtsai", "from": "duplicate"},
        }
        assert body["moves"] == {
            "enrollments": 1, "attendances": 2, "memberships": 3, "addresses": 2,
            "notes": 1, "statuses": 1, "registrations": 1,
        }

        # Merge Samuel into Sam, then apply two picks the way the screen does: as an edit.
        assert _merge(client, r.samuel, r.sam).status_code == 200
        fresh = client.get(f"{API}{r.sam.id}/").json()
        fresh["infos"]["fixed"]["grade"] = 16
        response = target(client, r.sam).patch(
            f"{API}{r.sam.id}/", {"first_name": "Samuel", "infos": fresh["infos"]}, format="json"
        )
        assert response.status_code == 200, response.content

        sam = _fresh(r.sam)
        assert (sam.first_name, sam.actual_birthday, sam.photo.name) == ("Samuel", date(2008, 6, 22), "attendee_portrait/sam.jpg")
        assert sam.infos["names"]["original"] == "Samuel Tsai"
        assert sam.infos["fixed"] == {"grade": 16, "insurer": "Kaiser", "food_pref": "peanut allergy"}
        after_first = {
            "phone1": "+15105550107", "phone2": "+15105550199",
            "email1": "sam@example.org", "email2": "sam2@example.org",
            "wechat1": "sam_t", "line1": "samtsai",
        }
        assert sam.infos["contacts"] == after_first
        assert sam.user_id == r.login.id
        assert sam.infos["schedulers"] == {str(r.parent.id): True}
        assert _fresh(r.child).infos["emergency_contacts"] == {str(sam.id): True}
        assert r.enrollments(sam) == [r.meet.display_name]
        assert r.check_ins(sam) == [r.gatherings[0].start, r.gatherings[1].start]
        assert r.folks(sam) == ["Peter's friends", "Tsai household", "Tsai household 2"]
        assert r.places(sam) == ["grandma", "home"]
        assert (r.linked(Note, sam), r.linked(Past, sam)) == (2, 2)
        assert Registration.objects.get(pk=r.registration.pk).registrant_id == sam.id
        assert Attending.objects.get(registration=r.registration).attendee_id == sam.id
        gone = client.get(f"{API}{r.samuel.id}/")
        assert gone.status_code == 410 and gone.json()["merged_into"] == str(sam.id)

        # Merge Sammy into the merged record: no picks this time.
        assert _preview(client, r.sammy, sam).json()["primary"]["id"] == str(sam.id)
        assert _merge(client, r.sammy, sam).status_code == 200
        sam = _fresh(r.sam)
        assert sam.infos["fixed"] == {"grade": 16, "insurer": "Kaiser", "food_pref": "peanut allergy", "mobility": 1}
        assert sam.infos["contacts"] == {**after_first, "phone3": "+15105550300"}
        assert r.enrollments(sam) == sorted([r.meet.display_name, r.sunday_school.display_name])
        assert r.linked(Note, sam) == 3
        assert client.get(f"{API}{r.sammy.id}/").json()["merged_into"] == str(sam.id)

        # Undo the last merge only: Sammy comes back, Samuel stays merged, the picks stay.
        assert _unmerge(client, r.sammy).status_code == 200
        sam, sammy = _fresh(r.sam), _fresh(r.sammy)
        assert not sammy.is_removed and sammy.merged_into_id is None
        assert r.enrollments(sammy) == [r.sunday_school.display_name]
        assert r.linked(Note, sammy) == 1
        assert sam.first_name == "Samuel"
        assert sam.infos["fixed"] == {"grade": 16, "insurer": "Kaiser", "food_pref": "peanut allergy"}
        assert sam.infos["contacts"] == after_first
        assert sam.user_id == r.login.id
        assert r.enrollments(sam) == [r.meet.display_name]
        assert r.folks(sam) == ["Peter's friends", "Tsai household", "Tsai household 2"]
        assert r.linked(Note, sam) == 2
        assert client.get(f"{API}{r.samuel.id}/").status_code == 410
        assert client.get(f"{API}{r.sammy.id}/").status_code == 200

    def test_a_chain_of_merges_collapses_and_unmerges_link_by_link(self, golden, token_client):
        r = Records(golden)
        client = token_client("golden_data_organizer")

        # Sammy into Samuel, then Samuel into Sam: Sammy's link ends at Sam.
        assert _merge(client, r.sammy, r.samuel).status_code == 200
        assert _fresh(r.samuel).infos["contacts"]["phone3"] == "+15105550300"
        assert _merge(client, r.samuel, r.sam).status_code == 200
        sam = _fresh(r.sam)
        assert [sam.infos["contacts"][key] for key in ("phone1", "phone2", "phone3")] == ["+15105550107", "+15105550199", "+15105550300"]
        assert r.enrollments(sam) == sorted([r.meet.display_name, r.sunday_school.display_name])
        assert client.get(f"{API}{r.sammy.id}/").json()["merged_into"] == str(sam.id)

        # Undo the last link: Samuel is back, still holding Sammy; Sammy's link ends at Samuel again.
        assert _unmerge(client, r.samuel).status_code == 200
        sam, samuel = _fresh(r.sam), _fresh(r.samuel)
        assert sam.infos["contacts"] == {"phone1": "+15105550107", "email1": "sam@example.org", "WeChat1": "sam_t"}
        assert r.enrollments(sam) == [r.meet.display_name]
        assert samuel.infos["contacts"]["phone3"] == "+15105550300"
        assert r.enrollments(samuel) == sorted([r.meet.display_name, r.sunday_school.display_name])
        assert client.get(f"{API}{r.sammy.id}/").json()["merged_into"] == str(samuel.id)
        assert client.get(f"{API}{r.samuel.id}/").status_code == 200
