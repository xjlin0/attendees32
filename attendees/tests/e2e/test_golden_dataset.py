"""The golden congregation is what it claims to be.

These are not view tests — they check the dataset itself, so that every later
e2e assertion rests on a census that has been verified once.  They also pin the
application behaviour the builder relies on: the four post-save signals that
turn one record into its counterpart.
"""

import pytest

from attendees.occasions.models import Attendance, Gathering, Meet, Price
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Folk,
    FolkAttendee,
    Note,
    Past,
    Registration,
)
from attendees.tests.golden.constants import (
    AttendanceCategory,
    DIVISION_CHINESE,
    DIVISION_CROSSING,
    DIVISION_JUNIOR,
    FolkCategory,
    MeetSlugs,
    NoteCategory,
    ORGANIZATION_ID,
    Relations,
    StatusCategory,
)
from attendees.tests.golden.roster import CHILD, CHINESE_ADULT, ENGLISH_ADULT, YOUTH

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------- census
class TestCensus:
    def test_the_church_has_350_living_members(self, golden):
        assert Attendee.objects.filter(
            division__organization_id=ORGANIZATION_ID
        ).count() == 350

    def test_each_bucket_lands_on_its_target(self, golden):
        assert len(golden.roster.bucket(CHINESE_ADULT)) == 200
        assert len(golden.roster.bucket(ENGLISH_ADULT)) == 100
        assert len(golden.roster.bucket(YOUTH)) == 25
        assert len(golden.roster.bucket(CHILD)) == 25

    def test_buckets_map_onto_divisions(self, golden):
        by_division = {
            DIVISION_CHINESE: 200,
            DIVISION_CROSSING: 125,  # 100 English adults + 25 youth
            DIVISION_JUNIOR: 25,
        }
        for division_id, expected in by_division.items():
            assert (
                Attendee.objects.filter(division_id=division_id).count() == expected
            ), f"division {division_id}"

    def test_the_departed_household_is_soft_deleted_not_gone(self, golden):
        departed = [
            golden.attendee(key).id
            for key in ("peng_jinlong", "peng_wanru", "peng_lily")
        ]
        assert Attendee.objects.filter(pk__in=departed).count() == 0
        assert Attendee.all_objects.filter(pk__in=departed, is_removed=True).count() == 3
        folk_id = golden.folk("HH_DEPARTED").id
        assert Folk.objects.filter(pk=folk_id).count() == 0
        assert Folk.all_objects.filter(pk=folk_id, is_removed=True).count() == 1

    def test_ten_chinese_adults_also_sit_in_the_english_service(self, golden):
        english = Meet.objects.get(slug=MeetSlugs.ENGLISH_SERVICE)
        chinese = Meet.objects.get(slug=MeetSlugs.CHINESE_SERVICE)
        both = (
            Attendee.objects.filter(
                division_id=DIVISION_CHINESE,
                attendings__attendingmeet__meet=english,
            )
            .filter(attendings__attendingmeet__meet=chinese)
            .distinct()
        )
        assert both.count() == 10

    def test_every_attendee_carries_a_romanised_and_a_han_name(self, golden):
        grace = golden.attendee("chen_grace")
        assert grace.infos["names"]["original"] == "Grace Chen 陳明恩"
        assert grace.infos["names"]["romanization"] == "Grace Chen Chen Ming En"
        # opencc_convert is on for this organization, so search works either way.
        assert grace.infos["names"]["traditional"] == "Grace Chen 陳明恩"
        assert grace.infos["names"]["simplified"] == "Grace Chen 陈明恩"

    def test_a_surname_is_reachable_by_two_romanisations(self, golden):
        """陳 turns up as both Chen and Chan, exactly as the PCO exports show."""
        assert Attendee.objects.filter(last_name="Chen").exists()
        assert Attendee.objects.filter(last_name="Chan").exists()
        assert Attendee.objects.filter(last_name2="陳").count() > 2


# -------------------------------------------------------------------- families
class TestFamilies:
    def test_every_hand_authored_household_was_built(self, golden):
        from attendees.tests.golden.roster import HAND_AUTHORED_KEYS

        for key in HAND_AUTHORED_KEYS:
            folk = golden.folk(key)
            assert Folk.all_objects.filter(pk=folk.pk).exists(), key
            assert FolkAttendee.all_objects.filter(folk=folk).exists(), key

    def test_three_generations_live_in_one_folk(self, golden):
        folk = golden.folk("HH_CHEN_THREE_GEN")
        roles = {
            fa.attendee.first_name: fa.role.title
            for fa in FolkAttendee.all_objects.filter(folk=folk)
        }
        assert roles == {
            "Zhiming": "husband",
            "Shufen": "wife",
            "Grace": "daughter",
            "Joshua": "son",
            "Guoqiang": "father",
            "Guizhi": "mother",
        }

    def test_the_grandmother_is_dead_and_her_membership_finished(self, golden):
        grandmother = golden.attendee("chen_guizhi")
        assert grandmother.deathday is not None
        assert grandmother.is_removed is False  # a death is not a deletion
        membership = FolkAttendee.objects.get(
            folk=golden.folk("HH_CHEN_THREE_GEN"), attendee=grandmother
        )
        assert membership.finish is not None

    def test_family_members_resolve_through_the_folk(self, golden):
        grace = golden.attendee("chen_grace")
        names = {member.first_name for member in grace.family_members}
        assert {"Zhiming", "Shufen", "Grace", "Joshua", "Guoqiang", "Guizhi"} == names

    def test_a_blended_family_carries_step_and_half_relations(self, golden):
        folk = golden.folk("HH_WONG_BLENDED")
        roles = {
            fa.attendee.first_name: fa.role.title
            for fa in FolkAttendee.objects.filter(folk=folk)
        }
        assert roles["Chloe"] == "step sister"
        assert roles["Marcus"] == "son"
        half = golden.folk("OTHER_WONG_HALF_SIBLINGS")
        assert half.category_id == FolkCategory.OTHER
        assert set(
            FolkAttendee.objects.filter(folk=half).values_list("role__title", flat=True)
        ) == {"hidden", "half sister", "step sister"}

    def test_a_parachute_student_is_a_ward_not_a_son(self, golden):
        kevin = golden.attendee("xu_kevin")
        membership = FolkAttendee.objects.get(
            folk=golden.folk("HH_XU_GUARDIAN"), attendee=kevin
        )
        assert membership.role_id == Relations.WARD
        guardians = FolkAttendee.objects.filter(
            folk=golden.folk("OTHER_XU_GUARDIANSHIP"), role_id=Relations.GUARDIAN
        )
        assert guardians.count() == 2

    def test_divorced_parents_share_children_across_two_households(self, golden):
        mother = golden.attendee("liu_meiling")
        father = golden.attendee("liu_yongkang")
        assert set(mother.families.values_list("id", flat=True)) != set(
            father.families.values_list("id", flat=True)
        )
        ex_spouses = golden.folk("OTHER_LIU_EX_SPOUSES")
        assert set(
            FolkAttendee.objects.filter(folk=ex_spouses).values_list(
                "attendee_id", flat=True
            )
        ) == {mother.id, father.id}

    def test_four_generations_down_the_female_line(self, golden):
        folk = golden.folk("HH_GUO_FOUR_GEN")
        assert FolkAttendee.objects.filter(folk=folk).count() == 4
        ages = sorted(
            fa.attendee.age() or 0
            for fa in FolkAttendee.objects.filter(folk=folk)
        )
        assert ages[0] < 5 and ages[-1] > 90

    def test_a_foster_placement_uses_caregiver_and_care_receiver(self, golden):
        folk = golden.folk("HH_FOSTER_CARE")
        roles = set(
            FolkAttendee.objects.filter(folk=folk).values_list("role_id", flat=True)
        )
        assert roles == {Relations.CAREGIVER, Relations.CARE_RECEIVER}

    def test_a_carpool_spans_three_households(self, golden):
        carpool = golden.folk("HH_CARPOOL_EAST")
        assert carpool.category_id == FolkCategory.CARPOOL
        memberships = FolkAttendee.objects.filter(folk=carpool)
        assert memberships.filter(role_id=Relations.DRIVER).count() == 1
        assert memberships.filter(role_id=Relations.PASSENGER).count() == 3

    def test_roommates_are_an_other_folk_not_a_family(self, golden):
        flat = golden.folk("HH_GRAD_ROOMMATES")
        assert flat.category_id == FolkCategory.OTHER
        assert FolkAttendee.objects.filter(folk=flat).count() == 3

    def test_saving_an_attendee_files_them_into_a_hidden_non_family_folk(self, golden):
        """The Attendee post-save signal, exercised 350 times over."""
        grace = golden.attendee("chen_grace")
        hidden = grace.folks.filter(category_id=FolkCategory.OTHER).first()
        assert hidden is not None
        assert hidden.display_name.endswith("other")
        assert FolkAttendee.objects.get(
            folk=hidden, attendee=grace
        ).role_id == Relations.HIDDEN

    def test_every_family_has_a_street_address(self, golden):
        families = Folk.objects.filter(
            category_id=FolkCategory.FAMILY, division__organization_id=ORGANIZATION_ID
        )
        assert families.count() >= 140
        with_address = [folk for folk in families if folk.places.exists()]
        assert len(with_address) == families.count()


# ------------------------------------------------------------------ attributes
class TestAttendeeAttributes:
    def test_an_unknown_birth_year_is_the_1800_placeholder(self, golden):
        widow = golden.attendee("wang_yulan")
        assert widow.actual_birthday is None
        assert str(widow.estimated_birthday) == "1800"
        assert widow.age() is None  # the placeholder must not become an age of 226

    def test_partial_birthdays_are_supported(self, golden):
        assert str(golden.attendee("chen_guoqiang").estimated_birthday).isdigit()
        assert "-" in str(golden.attendee("guo_mingzhu").estimated_birthday)

    def test_an_actual_birthday_produces_the_expected_age(self, golden):
        assert golden.attendee("chen_grace").age() == 15
        assert golden.attendee("chen_joshua").age() == 9

    def test_children_and_youth_carry_a_grade(self, golden):
        assert golden.attendee("chen_grace").infos["fixed"]["school_grade"] == 9
        assert golden.attendee("chen_grace").infos["fixed"]["grade"] == 15  # G9
        assert golden.attendee("chen_joshua").infos["fixed"]["grade"] == 9  # G3
        assert "grade" not in golden.attendee("chen_zhiming").infos["fixed"]

    def test_junior_ministry_children_carry_an_insurer(self, golden):
        children = Attendee.objects.filter(division_id=DIVISION_JUNIOR)
        assert all(child.infos["fixed"].get("insurer") for child in children)

    def test_allergies_and_medical_notes_are_tracked(self, golden):
        joshua = golden.attendee("chen_joshua")
        assert joshua.infos["fixed"]["food_pref"] == "peanut allergy"
        assert joshua.infos["fixed"]["medical"] == "carries an epi-pen"

    def test_mobility_is_tracked_for_the_people_who_need_it(self, golden):
        assert golden.attendee("wang_yulan").infos["fixed"]["mobility"] == 3
        assert golden.attendee("chen_guoqiang").infos["fixed"]["mobility"] == 1

    def test_contact_details_render_through_the_model_helpers(self, golden):
        zhiming = golden.attendee("chen_zhiming")
        assert "chen_zhiming@example.org" in zhiming.self_email_addresses
        assert "chen_zhiming.alt@example.net" in zhiming.self_email_addresses
        assert zhiming.self_phone_numbers.count("+") == 2

    def test_some_households_have_no_email_at_all(self, golden):
        tsai = golden.attendee("tsai_shixiang")
        assert tsai.self_email_addresses == ""
        assert tsai.self_phone_numbers != ""

    def test_emergency_contacts_resolve_to_attendees(self, golden):
        joshua = golden.attendee("chen_joshua")
        contacts = set(
            joshua.get_relative_emergency_contacts().values_list("first_name", flat=True)
        )
        assert contacts == {"Zhiming", "Shufen"}
        assert "Zhiming" in joshua.parents_notifiers_names

    def test_a_caregiver_supplies_the_contact_details_of_a_ward(self, golden):
        daniel = golden.attendee("hu_daniel")
        assert "ma_liyun@example.org" in daniel.caregiver_email_addresses

    def test_schedulers_can_see_and_change_a_child_schedule(self, golden):
        parent = golden.attendee("chen_zhiming")
        child = golden.attendee("chen_joshua")
        assert child.can_be_scheduled_by(str(parent.id))
        assert parent.can_schedule_attendee(str(child.id))
        scheduled = set(parent.scheduling_attendees().values_list("first_name", flat=True))
        assert {"Zhiming", "Grace", "Joshua"} <= scheduled

    def test_a_stranger_cannot_schedule_someone_else(self, golden):
        stranger = golden.attendee("wong_wilson")
        child = golden.attendee("chen_joshua")
        assert not child.can_be_scheduled_by(str(stranger.id))

    def test_genders_cover_all_three_choices(self, golden):
        genders = set(Attendee.objects.values_list("gender", flat=True))
        assert {"MALE", "FEMALE"} <= genders


# ------------------------------------------------------- statuses and history
class TestChurchStatuses:
    def test_baptisms_are_recorded_as_pasts(self, golden):
        baptisms = Past.objects.filter(category_id=StatusCategory.BAPTIZED)
        assert baptisms.count() > 150
        assert baptisms.filter(object_id=str(golden.attendee("chen_grace").id)).exists()

    def test_a_baptism_past_opens_the_baptised_participation(self, golden):
        """``past_category_to_attendingmeet_meet`` maps category 5 to meet 16."""
        meet = Meet.objects.get(slug=MeetSlugs.BAPTIZED)
        grace = golden.attendee("chen_grace")
        assert AttendingMeet.objects.filter(
            meet=meet, attending__attendee=grace
        ).exists()

    def test_a_believer_participation_writes_the_past_back(self, golden):
        """``Meet.infos.automatic_creation.Past`` maps meet 17 to category 4."""
        believers = AttendingMeet.objects.filter(
            meet__slug=MeetSlugs.BELIEVER
        ).select_related("attending__attendee")
        assert believers.exists()
        for attending_meet in believers[:10]:
            assert Past.objects.filter(
                object_id=str(attending_meet.attending.attendee_id),
                category_id=StatusCategory.RECEIVE,
            ).exists()

    def test_membership_visitors_and_catechumens_all_appear(self, golden):
        for category_id in (
            StatusCategory.MEMBER,
            StatusCategory.VISITOR,
            StatusCategory.CATECHUMEN,
            StatusCategory.INTERESTED,
            StatusCategory.DISBELIEVER,
            StatusCategory.COWORKER,
            StatusCategory.DEACON,
        ):
            assert Past.objects.filter(
                category_id=category_id
            ).exists(), f"no Past of category {category_id}"

    def test_the_directory_participation_flips_the_family_flag(self, golden):
        """``Meet.infos.automatic_modification.Folk`` on the 通訊錄 meet."""
        assert golden.folk("HH_CHEN_THREE_GEN").infos["print_directory"] is True
        Folk.objects.get(pk=golden.folk("HH_NEW_IMMIGRANT").pk)
        assert golden.folk("HH_NEW_IMMIGRANT").infos["print_directory"] is False

    def test_education_history_is_recorded(self, golden):
        assert Past.objects.filter(category__type="education").count() > 30
        assert Past.objects.filter(
            object_id=str(golden.attendee("zhang_zhongxin").id),
            category__type="education",
        ).exists()

    def test_notes_exist_at_every_confidentiality_level(self, golden):
        for category_id in (
            NoteCategory.PUBLIC, NoteCategory.COWORKER, NoteCategory.COUNSELING
        ):
            assert Note.objects.filter(category_id=category_id).exists()

    def test_a_counseling_note_names_the_reader_allowed_to_open_it(self, golden):
        """``show_secret`` is keyed by attendee id — that is what the API filters on."""
        counselor_attendee_id = str(golden.attendee("xu_jianguo").id)
        note = Note.objects.get(
            object_id=str(golden.attendee("liu_meiling").id),
            category_id=NoteCategory.COUNSELING,
        )
        assert note.infos["show_secret"] == {counselor_attendee_id: True}
        # The same body is also filed as a Past, which is what the attendee
        # page's note tab reads.
        past = Past.objects.get(
            object_id=str(golden.attendee("liu_meiling").id),
            category_id=NoteCategory.COUNSELING,
        )
        assert past.infos["show_secret"] == {counselor_attendee_id: True}


# --------------------------------------------------------------- participation
class TestParticipation:
    def test_saving_an_attendee_opens_an_attending(self, golden):
        for key in ("chen_grace", "wong_wilson", "wang_yulan"):
            assert Attending.objects.filter(
                attendee=golden.attendee(key), category="auto-created"
            ).exists()

    def test_worship_participation_covers_the_whole_church(self, golden):
        worshippers = (
            Attendee.objects.filter(
                attendings__attendingmeet__meet__slug__in=[
                    MeetSlugs.CHINESE_SERVICE, MeetSlugs.ENGLISH_SERVICE
                ]
            )
            .distinct()
            .count()
        )
        assert worshippers == 349  # everyone except the attendee who died

    def test_inactive_paused_remote_and_leave_are_all_represented(self, golden):
        for category_id in (
            AttendanceCategory.SCHEDULED,
            AttendanceCategory.INACTIVE,
            AttendanceCategory.PAUSED,
            AttendanceCategory.REMOTE,
            AttendanceCategory.LEAVE,
            AttendanceCategory.PRIMARY,
            AttendanceCategory.SECONDARY,
            AttendanceCategory.ACTIVE,
            AttendanceCategory.CONFIRMED,
        ):
            assert AttendingMeet.objects.filter(
                category_id=category_id
            ).exists(), f"no AttendingMeet of category {category_id}"

    def test_an_inactive_participation_has_already_finished(self, golden):
        from attendees.persons.models import Utility

        inactive = AttendingMeet.objects.filter(
            category_id=AttendanceCategory.INACTIVE
        ).first()
        assert inactive.finish < Utility.now_with_timezone()

    def test_the_choir_has_all_four_sections(self, golden):
        sections = set(
            AttendingMeet.objects.filter(meet__slug=MeetSlugs.CHINESE_CHOIR)
            .exclude(team=None)
            .values_list("team__display_name", flat=True)
        )
        assert len(sections) == 4

    def test_every_chinese_fellowship_has_members(self, golden):
        from attendees.tests.golden.constants import CHINESE_FELLOWSHIP_MEET_SLUGS

        for slug in CHINESE_FELLOWSHIP_MEET_SLUGS:
            assert AttendingMeet.objects.filter(
                meet__slug=slug
            ).exists(), f"nobody in {slug}"

    def test_children_are_grouped_by_grade(self, golden):
        rock = AttendingMeet.objects.filter(
            meet__slug=MeetSlugs.THE_ROCK, character_id=1
        ).exclude(team=None)
        assert rock.exists()
        joshua = golden.attendee("chen_joshua")
        assert rock.get(attending__attendee=joshua).team.slug == "cfcch_kid_rock_g3"

    def test_the_youth_ministry_splits_middle_and_high_school(self, golden):
        teams = set(
            AttendingMeet.objects.filter(meet=golden.meets["youth_group"])
            .exclude(team=None)
            .values_list("team__display_name", flat=True)
        )
        assert {"Middle School 6-8", "High School 9-12"} <= teams

    def test_participations_carry_free_form_infos(self, golden):
        assert AttendingMeet.objects.filter(
            infos__has_key="kid_points"
        ).exists()


# ------------------------------------------------------------------- retreat
class TestSummerRetreat:
    def test_prices_are_configured(self, golden):
        assert Price.objects.filter(
            assembly__slug="cfcch_summer_retreat_2025"
        ).count() == 4

    def test_households_register_together(self, golden):
        assert Registration.objects.count() > 50
        multi = [
            registration
            for registration in Registration.objects.all()
            if registration.attending_set.count() > 1
        ]
        assert multi, "no household registered more than one person"

    def test_registered_attendings_carry_a_price_and_bed_needs(self, golden):
        attending = (
            Attending.objects.filter(registration__isnull=False, price__isnull=False)
            .first()
        )
        assert attending.infos["bed_needs"] in (0, 1)
        assert attending.price.price_value >= 0

    def test_some_registrations_donated_or_used_credit(self, golden):
        infos = [registration.infos for registration in Registration.objects.all()]
        assert any(info["donation"] != "0.00" for info in infos)
        assert any(info["credit"] != "0.00" for info in infos)
        assert {"online", "paper"} == {info["apply_type"] for info in infos}

    def test_a_few_people_pulled_out(self, golden):
        assert Attending.objects.filter(category="not_going").exists()


# ------------------------------------------------------------------- history
class TestAttendanceHistory:
    def test_eight_weeks_of_sundays_for_four_meets(self, golden):
        assert len(golden.gatherings) == 32

    def test_attendances_cover_present_absent_remote_and_leave(self, golden):
        categories = set(
            Attendance.objects.values_list("category_id", flat=True).distinct()
        )
        assert {
            AttendanceCategory.ATTENDED,
            AttendanceCategory.ABSENT,
            AttendanceCategory.REMOTE,
            AttendanceCategory.LEAVE,
        } <= categories

    def test_attendance_volume_is_realistic(self, golden):
        assert 2000 < Attendance.objects.count() < 4000

    def test_the_latest_childrens_register_is_still_open(self, golden):
        """Some children arrived and nobody has signed for them yet.

        Every other week is closed off, so this is the one gathering that looks
        the way the roll-call screen looks while it is in use — which is the
        only state in which the check-out pad can be reached at all.
        """
        the_rock = golden.meets["the_rock"]
        open_rows = Attendance.objects.filter(
            gathering__meet=the_rock, start__isnull=False, finish__isnull=True
        )
        assert open_rows.count() > 0
        # And only in the most recent week: the history behind it is settled.
        assert open_rows.values_list("gathering_id", flat=True).distinct().count() == 1
        assert (
            open_rows.first().gathering.start.date()
            == Attendance.objects.filter(gathering__meet=the_rock)
            .order_by("-gathering__start")
            .first()
            .gathering.start.date()
        )

    def test_gatherings_know_their_room(self, golden):
        gathering = Gathering.objects.filter(
            meet__slug=MeetSlugs.CHINESE_SERVICE
        ).first()
        assert gathering.site is not None


# -------------------------------------------------------------------- logins
class TestPersonas:
    def test_every_persona_exists(self, golden, personas):
        for username in personas:
            assert golden.user(username).username == username

    def test_the_data_organizer_is_privileged(self, golden):
        user = golden.user("golden_data_organizer")
        assert user.privileged() is True
        assert user.is_data_admin() is True
        assert user.can_see_all_organizational_meets_attendees() is True

    def test_the_counselor_is_privileged_but_not_a_data_admin(self, golden):
        user = golden.user("golden_counselor")
        assert user.privileged() is True
        assert user.is_counselor() is True
        assert user.is_data_admin() is False

    def test_an_ordinary_member_is_not_privileged(self, golden):
        user = golden.user("golden_member")
        assert user.privileged() is False
        assert user.can_see_all_organizational_meets_attendees() is False
        assert user.attendee.first_name == "Zhiming"

    def test_a_login_without_an_attendee_is_supported(self, golden):
        user = golden.user("golden_unaffiliated")
        assert not hasattr(user, "attendee")
        assert user.attendee_uuid_str() == ""

    def test_an_outsider_has_no_organization(self, golden):
        assert golden.user("golden_outsider").organization is None
