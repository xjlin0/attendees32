"""Merging one attendee into another: attendance moves, clashing rows retire,
chains terminate."""

import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from address.models import Address

from attendees.occasions.models import Assembly, Attendance, Character, Gathering, Meet
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
from attendees.persons.models.enum import GenderEnum
from attendees.persons.services.merge_service import (
    AttendeeMergeService,
    MergeRefused,
)
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization, Place


@pytest.mark.django_db
class TestAttendeeMergeService:
    def setup_method(self):
        self.organization = Organization.objects.create(
            display_name="Test Organization", slug="test-org"
        )
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group,
        )
        self.category = Category.objects.create(id=25, display_name="Test Category")
        self.family_category = Category.objects.create(id=0, display_name="Family")
        self.relation = Relation.objects.create(
            id=0, title="test relation", gender=GenderEnum.UNSPECIFIED.value
        )
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )

        self.scheduled = Category.objects.create(id=1, display_name="Scheduled")
        self.attendee_type = ContentType.objects.get_for_model(Attendee)
        self.now = datetime.now(timezone.utc)
        site = ContentType.objects.get_for_model(Assembly)
        self.merge_character = Character.objects.create(
            assembly=self.assembly, display_name="Participant", slug="merge-participant", type="normal"
        )
        self.merge_meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.merge_character,
            shown_audience=True,
            audience_editable=True,
            start=self.now,
            finish=self.now + timedelta(days=30),
            display_name="Merge Meet",
            slug="merge-meet",
            site_type=site,
            site_id=str(self.assembly.id),
        )
        self.gathering = Gathering.objects.create(
            meet=self.merge_meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Tonight",
            site_type=site,
            site_id=str(self.assembly.id),
        )

        self.primary = self._attendee("Ava")
        self.duplicate = self._attendee("Ava")

    def _attendee(self, first_name, **fields):
        return Attendee.objects.create(
            first_name=first_name, last_name="Chen", division=self.division, gender="unspecified", **fields
        )

    def _enroll(self, attending):
        return AttendingMeet.objects.create(
            attending=attending,
            meet=self.merge_meet,
            character=self.merge_character,
            category=self.scheduled,
            start=self.now,
            finish=self.now + timedelta(days=30),
        )

    def _check_in(self, attending, start=None):
        return Attendance.objects.create(
            gathering=self.gathering,
            attending=attending,
            character=self.merge_character,
            start=start or self.now,
            finish=self.now + timedelta(hours=2),
        )

    def _linked(self, model, attendee, **fields):
        return model.objects.create(
            content_type=self.attendee_type,
            object_id=str(attendee.id),
            organization=self.organization,
            **fields,
        )

    def test_moves_attendance_to_the_primary(self):
        # Every attendee gets one registration-less attending at creation.
        ours = self.duplicate.attendings.get()
        enrollment = self._enroll(ours)
        attendance = self._check_in(ours)

        AttendeeMergeService.merge(self.duplicate, self.primary)

        theirs = self.primary.attendings.get()
        for row in (enrollment, attendance):
            row.refresh_from_db()
            assert row.attending_id == theirs.id and not row.is_removed

    def test_retires_a_row_the_primary_already_has(self):
        """Unique where live, so the clashing row is retired rather than moved."""
        registration = Registration.objects.create(
            registrant=self.primary, assembly=self.assembly
        )
        theirs = Attending.objects.create(attendee=self.primary, registration=registration)
        ours = Attending.objects.create(attendee=self.duplicate, registration=registration)

        AttendeeMergeService.merge(self.duplicate, self.primary)

        ours.refresh_from_db()
        theirs.refresh_from_db()
        assert ours.is_removed
        assert not theirs.is_removed
        assert theirs.attendee_id == self.primary.id

    def test_moves_family_membership(self):
        folk = Folk.objects.create(
            category=self.family_category, division=self.division, display_name="Chen family"
        )
        membership = FolkAttendee.objects.create(
            folk=folk, attendee=self.duplicate, role=self.relation
        )

        AttendeeMergeService.merge(self.duplicate, self.primary)

        membership.refresh_from_db()
        assert membership.attendee_id == self.primary.id

    def test_keeps_the_duplicate_as_a_tombstone(self):
        AttendeeMergeService.merge(self.duplicate, self.primary)

        # Kept, not deleted: the old id stays followable.
        buried = Attendee.all_objects.get(pk=self.duplicate.pk)
        assert buried.is_removed
        assert buried.merged_into_id == self.primary.id
        assert not Attendee.objects.filter(pk=self.duplicate.pk).exists()

    def test_follows_a_chain_to_its_end(self):
        third = Attendee.objects.create(
            first_name="Ava", last_name="Chen", division=self.division, gender="unspecified"
        )
        # A into B, then B into C.
        AttendeeMergeService.merge(self.duplicate, self.primary)
        AttendeeMergeService.merge(self.primary, third)

        primary, was_merged = AttendeeMergeService.resolve(self.duplicate.pk)
        assert was_merged
        assert primary.id == third.id

    def test_says_gone_when_the_trail_ends_nowhere(self):
        AttendeeMergeService.merge(self.duplicate, self.primary)
        self.primary.is_removed = True
        self.primary.save(update_fields=["is_removed"])

        primary, was_merged = AttendeeMergeService.resolve(self.duplicate.pk)
        assert was_merged
        assert primary is None

    def test_a_circle_is_gone_rather_than_a_hang(self):
        AttendeeMergeService.merge(self.duplicate, self.primary)
        # Only hand-edited data can hold a cycle; the bound makes it an answer.
        self.primary.merged_into = self.duplicate
        self.primary.save(update_fields=["merged_into"])

        assert AttendeeMergeService.primary_of(self.duplicate) is None

    def test_a_second_merge_re_points_the_earlier_duplicates(self):
        """A into B, then B into C: A points straight at C, no walk needed."""
        third = Attendee.objects.create(
            first_name="Ava", last_name="Chen", division=self.division, gender="unspecified"
        )
        AttendeeMergeService.merge(self.duplicate, self.primary)
        AttendeeMergeService.merge(self.primary, third)

        first = Attendee.all_objects.get(pk=self.duplicate.pk)
        assert first.merged_into_id == third.pk
        # all_objects: the default manager hides soft-deleted tombstones.
        duplicates = Attendee.all_objects.filter(merged_into=third).values_list("pk", flat=True)
        assert set(duplicates) == {self.duplicate.pk, self.primary.pk}

    def test_refuses_a_merge_into_itself(self):
        with pytest.raises(MergeRefused):
            AttendeeMergeService.merge(self.duplicate, self.duplicate)

    def test_refuses_a_merge_across_organizations(self):
        other_org = Organization.objects.create(display_name="Other", slug="other-org")
        other_division = Division.objects.create(
            organization=other_org,
            display_name="Other Division",
            slug="other-division",
            audience_auth_group=Group.objects.create(name="Other Group"),
        )
        stranger = Attendee.objects.create(
            first_name="Ava", last_name="Chen", division=other_division, gender="unspecified"
        )

        with pytest.raises(MergeRefused):
            AttendeeMergeService.merge(self.duplicate, stranger)

    def test_refuses_a_merge_into_a_record_already_merged_away(self):
        third = Attendee.objects.create(
            first_name="Ava", last_name="Chen", division=self.division, gender="unspecified"
        )
        AttendeeMergeService.merge(self.primary, third)

        # Name the person, not the tombstone.
        with pytest.raises(MergeRefused):
            AttendeeMergeService.merge(self.duplicate, self.primary)

    def test_a_live_attendee_resolves_to_themselves(self):
        primary, was_merged = AttendeeMergeService.resolve(self.primary.pk)
        assert primary.id == self.primary.id
        assert not was_merged

    def test_folds_a_registration_less_attending_into_the_primarys(self):
        theirs = self.primary.attendings.get()
        ours = self.duplicate.attendings.get()
        enrollment = self._enroll(ours)
        attendance = self._check_in(ours)

        AttendeeMergeService.merge(self.duplicate, self.primary)

        for row in (enrollment, attendance, ours):
            row.refresh_from_db()
        assert enrollment.attending_id == theirs.id
        assert attendance.attending_id == theirs.id
        assert ours.is_removed
        assert self.primary.attendings.count() == 1

    def test_retires_an_enrollment_and_a_check_in_the_primary_already_has(self):
        theirs = self.primary.attendings.get()
        ours = self.duplicate.attendings.get()
        self._enroll(theirs)
        self._check_in(theirs)
        extra_enrollment = self._enroll(ours)
        extra_attendance = self._check_in(ours)
        later = self._check_in(ours, start=self.now + timedelta(minutes=30))

        AttendeeMergeService.merge(self.duplicate, self.primary)

        for row in (extra_enrollment, extra_attendance, later):
            row.refresh_from_db()
        assert extra_enrollment.is_removed
        assert extra_attendance.is_removed
        # A different time is a second check-in, not the same one twice.
        assert not later.is_removed and later.attending_id == theirs.id
        assert AttendingMeet.objects.filter(attending=theirs).count() == 1

    def test_moves_pasts_notes_and_addresses(self):
        past = self._linked(Past, self.duplicate, category=self.category, display_name="baptized")
        note = self._linked(Note, self.duplicate, category=self.category, body="peanut allergy")
        home = Address.objects.create(raw="1 Main St")
        shared = Address.objects.create(raw="2 Oak Ave")
        moved = self._linked(Place, self.duplicate, address=home, display_name="home")
        same = self._linked(Place, self.duplicate, address=shared, display_name="work")
        self._linked(Place, self.primary, address=shared, display_name="work")

        AttendeeMergeService.merge(self.duplicate, self.primary)

        for row in (past, note, moved):
            row.refresh_from_db()
            assert row.object_id == str(self.primary.id)
        same.refresh_from_db()
        assert same.is_removed

    def test_moves_the_login_and_refuses_two(self):
        login = User.objects.create(username="duplicate-login", email="duplicate@example.com")
        self.duplicate.user = login
        self.duplicate.save(update_fields=["user"])

        AttendeeMergeService.merge(self.duplicate, self.primary)

        self.primary.refresh_from_db()
        self.duplicate.refresh_from_db()
        assert self.primary.user_id == login.id
        assert self.duplicate.user_id is None

        third = self._attendee("Ava", user=User.objects.create(username="third-login", email="third@example.com"))
        with pytest.raises(MergeRefused, match="login"):
            AttendeeMergeService.merge(third, self.primary)

    def test_rekeys_references_held_by_other_attendees(self):
        parent = self._attendee("Mei")
        parent.infos["schedulers"] = {str(self.duplicate.id): True}
        parent.infos["emergency_contacts"] = {str(self.duplicate.id): True, str(self.primary.id): False}
        parent.save(update_fields=["infos"])

        AttendeeMergeService.merge(self.duplicate, self.primary)

        parent.refresh_from_db()
        assert parent.infos["schedulers"] == {str(self.primary.id): True}
        # The primary's own entry wins over the duplicate's.
        assert parent.infos["emergency_contacts"] == {str(self.primary.id): False}

    def test_retires_the_duplicates_hidden_folk(self):
        hidden = self.duplicate.folks.get(category_id=Attendee.NON_FAMILY_CATEGORY)

        AttendeeMergeService.merge(self.duplicate, self.primary)

        assert Folk.all_objects.get(pk=hidden.pk).is_removed
        assert not FolkAttendee.objects.filter(attendee=self.primary, folk=hidden).exists()
        assert self.primary.folks.filter(category_id=Attendee.NON_FAMILY_CATEGORY).count() == 1

    def test_records_what_moved(self):
        ours = self.duplicate.attendings.get()

        AttendeeMergeService.merge(self.duplicate, self.primary, by="coworker")

        record = Attendee.all_objects.get(pk=self.duplicate.pk).infos["merge"]
        assert record["into"] == str(self.primary.id)
        assert record["by"] == "coworker"
        assert record["moved"]["attendings"]["folded"][0]["attending"] == ours.id

    def test_unmerge_puts_everything_back(self):
        theirs = self.primary.attendings.get()
        ours = self.duplicate.attendings.get()
        self._enroll(theirs)
        enrollment = self._enroll(ours)  # clashes, so it is retired rather than moved
        attendance = self._check_in(ours)
        family = Folk.objects.create(
            category=self.family_category, division=self.division, display_name="Chen family"
        )
        membership = FolkAttendee.objects.create(folk=family, attendee=self.duplicate, role=self.relation)
        hidden = self.duplicate.folks.get(category_id=Attendee.NON_FAMILY_CATEGORY)
        past = self._linked(Past, self.duplicate, category=self.category, display_name="baptized")
        registration = Registration.objects.create(registrant=self.duplicate, assembly=self.assembly)
        login = User.objects.create(username="duplicate-login", email="duplicate@example.com")
        self.duplicate.user = login
        self.duplicate.save(update_fields=["user"])
        parent = self._attendee("Mei")
        parent.infos["schedulers"] = {str(self.duplicate.id): True}
        parent.save(update_fields=["infos"])
        earlier = self._attendee("Ava")
        AttendeeMergeService.merge(earlier, self.duplicate)

        AttendeeMergeService.merge(self.duplicate, self.primary)
        restored = AttendeeMergeService.unmerge(self.duplicate)

        assert restored.merged_into_id is None and not restored.is_removed
        assert "merge" not in restored.infos
        assert restored.infos["unmerged"][0]["into"] == str(self.primary.id)
        for row in (enrollment, attendance, ours, membership, past, registration, parent):
            row.refresh_from_db()
        assert enrollment.attending_id == ours.id and not enrollment.is_removed
        assert attendance.attending_id == ours.id and not attendance.is_removed
        assert not ours.is_removed
        assert membership.attendee_id == self.duplicate.id and not membership.is_removed
        assert not Folk.all_objects.get(pk=hidden.pk).is_removed
        assert past.object_id == str(self.duplicate.id)
        assert registration.registrant_id == self.duplicate.id
        self.primary.refresh_from_db()
        assert self.primary.user_id is None and restored.user_id == login.id
        assert parent.infos["schedulers"] == {str(self.duplicate.id): True}
        assert Attendee.all_objects.get(pk=earlier.pk).merged_into_id == self.duplicate.id
        assert self.primary.attendings.count() == 1

    def test_unmerge_keeps_what_the_primary_gained_since(self):
        AttendeeMergeService.merge(self.duplicate, self.primary)
        theirs = self.primary.attendings.get()
        since = self._enroll(theirs)

        AttendeeMergeService.unmerge(self.duplicate)

        since.refresh_from_db()
        assert since.attending_id == theirs.id and not since.is_removed

    def test_unmerge_is_refused_when_there_is_nothing_to_undo(self):
        with pytest.raises(MergeRefused, match="not merged"):
            AttendeeMergeService.unmerge(self.duplicate)

        AttendeeMergeService.merge(self.duplicate, self.primary)
        AttendeeMergeService.unmerge(self.duplicate)
        with pytest.raises(MergeRefused, match="not merged"):
            AttendeeMergeService.unmerge(self.duplicate)

        AttendeeMergeService.merge(self.duplicate, self.primary)
        tombstone = Attendee.all_objects.get(pk=self.duplicate.pk)
        del tombstone.infos["merge"]
        tombstone.save(update_fields=["infos"])
        with pytest.raises(MergeRefused, match="no record"):
            AttendeeMergeService.unmerge(tombstone)

