"""
Primary keys and slugs the golden dataset stands on.

Everything here already exists in ``fixtures/db_seed.json``; the golden builder
never invents a vocabulary row it can reuse.  Keeping the ids in one module
means a seed renumbering breaks one file instead of twenty.
"""

# ---------------------------------------------------------------- organization
ORGANIZATION_ID = 1  # CFCCH
ORGANIZATION_SLUG = "d7c8Fd_cfcc_hayward"
ARCHIVED_ORGANIZATION_ID = -1

# -------------------------------------------------------------------- division
DIVISION_UNSPECIFIED = 0
DIVISION_CHINESE = 1  # 中文部, the immigrant congregation
DIVISION_CROSSING = 2  # The Crossing, the English congregation
DIVISION_JUNIOR = 3  # Junior Ministry, the children's program
DIVISION_DATA = 5  # 資料部
DIVISION_CONFERENCE = 6  # 特會

DIVISION_SLUGS = {
    DIVISION_UNSPECIFIED: "cfcch_unspecified",
    DIVISION_CHINESE: "cfcch_chinese_ministry",
    DIVISION_CROSSING: "cfcch_crossing_ministry",
    DIVISION_JUNIOR: "cfcch_children_ministry",
    DIVISION_DATA: "cfcch_data_management",
    DIVISION_CONFERENCE: "cfcch_special_conference",
}


# ------------------------------------------------------------------- categories
class FolkCategory:
    FAMILY = 0
    OTHER = 25
    CARPOOL = 35


class StatusCategory:
    GENERAL = 3
    RECEIVE = 4  # 已信主, believer
    BAPTIZED = 5
    VISITOR = 19
    INTERESTED = 20
    CATECHUMEN = 21
    DISBELIEVER = 22
    COWORKER = 23
    DEACON = 24
    MEMBER = 37


class EducationCategory:
    POSTGRADUATE = 2
    PRIMARY = 16
    SECONDARY = 17
    ALTERNATIVE = 18
    COLLEGE = 30


class NoteCategory:
    PUBLIC = 11
    COWORKER = 12
    COUNSELING = 13


class CallCategory:
    PUBLIC = 14
    PRIVATE = 15


class AttendanceCategory:
    """Also used for AttendingMeet.category — the seed shares the vocabulary."""

    IMPORTER = -1
    SCHEDULED = 1
    ACTIVE = 6
    CONFIRMED = 7
    CANCELLED = 8
    ATTENDED = 9
    ABSENT = 10
    INACTIVE = 26
    PAUSED = 27
    PRIMARY = 28
    SECONDARY = 29
    REMOTE = 31
    LEAVE = 32


class AssemblyCategory:
    PUBLIC = 33
    INTERNAL = 34


CHECK_CATEGORY = 36


# -------------------------------------------------------------------- relations
class Relations:
    MASKED = -1
    HIDDEN = 0
    FATHER = 1
    MOTHER = 2
    SON = 3
    DAUGHTER = 4
    HUSBAND = 5
    WIFE = 6
    DRIVER = 7
    BROTHER = 8
    SISTER = 9
    HALF_BROTHER = 10
    HALF_SISTER = 11
    CAREGIVER = 12
    CARE_RECEIVER = 13
    SPOUSE = 14
    GUARDIAN = 15
    WARD = 16
    NEIGHBOR = 17
    FRIEND = 18
    LANDLORD = 19
    TENANT = 20
    MOTHER_IN_LAW = 21
    FATHER_IN_LAW = 22
    BROTHER_IN_LAW = 23
    SISTER_IN_LAW = 24
    UNSPECIFIED = 25
    EX_SPOUSE = 26
    CHILD = 27
    SELF = 28
    SIBLING = 29
    PARENT = 30
    SWEETHEART = 31
    STEP_BROTHER = 32
    STEP_SISTER = 33
    STEP_SIBLING = 34
    ENEMY = 35
    BOY_GIRL_FRIEND = 36
    CRUSH = 37
    PASSENGER = 38
    GRANDSON = 39
    GRANDDAUGHTER = 40


# ---------------------------------------------------------------------- meets
class MeetSlugs:
    ARCHIVED = "d7c8Fd_cfcch_congregation_archived"
    VISITOR = "d7c8Fd_cfcch_congregation_visitor"
    THE_ROCK = "d7c8Fd_cfcch_junior_regular_the_rock"
    LITTLE_FOOT = "d7c8Fd_cfcch_junior_regular_little_foot"
    CHINESE_CHOIR = "d7c8Fd_cfcch_chinese_choir"
    ENGLISH_SERVICE = "d7c8Fd_cfcch_congregation_english_worship_roster"
    SHINING_STAR = "d7c8Fd_cfcch_junior_shining_star"
    JUNIOR_RETREAT = "d7c8Fd_cfcch_junior_retreat"
    CHINESE_SERVICE = "d7c8Fd_cfcch_congregation_chinese_worship_roster"
    DIRECTORY = "d7c8Fd_cfcch_congregation_directory"
    MEMBER = "d7c8Fd_cfcch_congregation_member"
    RETREAT_ACCOMMODATION = "d7c8Fd_cfcch_summer_retreat_2025_accommodation"
    RETREAT_TRANSPORTATION = "d7c8Fd_cfcch_summer_retreat_2025_transportation"
    RETREAT_PANEL = "d7c8Fd_cfcch_summer_retreat_2025_panel"
    RETREAT_CHINESE_PROGRAM = "d7c8Fd_cfcch_summer_retreat_2025_chinese_program"
    RETREAT_JUNIOR_PROGRAM = "d7c8Fd_cfcch_summer_retreat_2025_junior_program"
    RETREAT_ENGLISH_PROGRAM = "d7c8Fd_cfcch_summer_retreat_2025_english_program"
    BAPTIZED = "d7c8Fd_cfcch_congregation_baptized"
    BELIEVER = "d7c8Fd_cfcch_congregation_believer"
    ADULT_SUNDAY_SCHOOL = "d7c8Fd_cfcch_adult_chinese_sunday_school"
    AFTER_SCHOOL_CLUB = "d7c8Fd_cfcch_junior_regular_after_school_club"
    LIBRARY = "d7c8Fd_cfcch_library_circulation"
    CATECHUMEN = "d7c8Fd_cfcch_congregation_catechumen"


CHINESE_FELLOWSHIP_MEET_SLUGS = (
    "d7c8Fd_cfcch_fellowship_ezra",
    "d7c8Fd_cfcch_chinese_bible_study",
    "d7c8Fd_cfcch_chinese_timothy_fellowship",
    "d7c8Fd_cfcch_chinese_RestaurantMinistry_fellowship",
    "d7c8Fd_cfcch_chinese_sister_fellowship",
    "d7c8Fd_cfcch_chinese_youngster_family_fellowship",
    "d7c8Fd_cfcch_chinese_caleb_fellowship",
    "d7c8Fd_cfcch_chinese_hayward_joy_group",
    "d7c8Fd_cfcch_chinese_oakland_renew_group",
    "d7c8Fd_cfcch_chinese_castro_valley_kind_group",
    "d7c8Fd_cfcch_chinese_pleasanton_faithful_group",
    "d7c8Fd_cfcch_chinese_fremont_confident_group",
)


# ----------------------------------------------------------------- assemblies
class AssemblySlugs:
    UNSPECIFIED = "cfcch_unspecified"
    JUNIOR_REGULAR = "cfcch_junior_regular_activity"
    CHINESE_WORSHIP_TEAM = "cfcch_chinese_worship_team"
    JUNIOR_SPECIAL = "cfcch_junior_special_activity"
    CONGREGATION_DATA = "cfcch_congregation_data"
    SUMMER_RETREAT = "cfcch_summer_retreat_2025"
    CROSSING_WORSHIP_TEAM = "cfcch_crossing_worship_team"
    CHINESE_FELLOWSHIP = "cfcch_chinese_fellowship"
    LIBRARY = "cfcch_data_library"
    CHINESE_SUNDAY_SCHOOL = "cfcch_chinese_sunday_school"
    # added by the golden builder, the seed has no English youth ministry
    CROSSING_YOUTH = "cfcch_crossing_youth"


# ----------------------------------------------------------------- characters
class Characters:
    JUNIOR_STUDENT = 1
    CHINESE_FELLOWSHIP_PARTICIPANT = 2
    CHOIR_SOLO = 3
    CHOIR_ACCOMPANIST = 4
    CHOIR_CONDUCTOR = 5
    CHOIR_MEMBER = 6
    JUNIOR_RETREAT_DRIVER = 8
    SG_LEADER_G2_G3 = 13
    SG_LEADER_G4_G5 = 14
    CONGREGATION = 15
    RETREAT_ATTENDEE = 16
    RETREAT_COWORKER = 17
    RETREAT_DRIVER = 18
    RETREAT_PANEL_MEMBER = 19
    RETREAT_PANEL_LEADER = 20
    RETREAT_PASSENGER = 21
    MEMBER = 22
    IN_DIRECTORY = 23
    BAPTISEE = 24
    BELIEVER = 25
    VISITOR = 26
    HEAD_COUNTER = 27
    STUDENT_FOOD = 28
    STUDENT_WATER = 29
    STUDENT_UTENCILS = 30
    STUDENT_PRESCHOOL_SERVER = 31
    ROCK_LG_LEADER_1 = 32
    ROCK_LG_LEADER_2 = 33
    ROCK_SG_KINDERGARTEN = 34
    ROCK_SG_G1 = 35
    ROCK_SG_G2 = 36
    ROCK_SG_G3 = 37
    ROCK_SG_G4 = 38
    ROCK_SG_G5 = 39
    ROCK_PRESCHOOL_P1 = 44
    LITTLE_FOOT_NURSERY_P1 = 46
    LITTLE_FOOT_NURSERY_P2 = 47
    LIBRARY_BORROWER = 48
    AFTER_SCHOOL_COWORKER = 49
    CATECHUMEN = 50
    CHINESE_FELLOWSHIP_LEADER = 51
    CHINESE_FELLOWSHIP_COWORKER = 52


ROCK_SMALL_GROUP_CHARACTER_BY_GRADE = {
    0: Characters.ROCK_SG_KINDERGARTEN,
    1: Characters.ROCK_SG_G1,
    2: Characters.ROCK_SG_G2,
    3: Characters.ROCK_SG_G3,
    4: Characters.ROCK_SG_G4,
    5: Characters.ROCK_SG_G5,
}


class TeamSlugs:
    ROCK_PRESCHOOL = "cfcch_kid_rock_preschool"
    ROCK_LARGE_GROUP = "cfcch_kid_rock_large_group"
    CHOIR_SOPRANO = "cfcch_chinese_choir_soprano"
    CHOIR_ALTO = "cfcch_chinese_choir_alto"
    CHOIR_TENOR = "cfcch_chinese_choir_tenor"
    CHOIR_BASS = "cfcch_chinese_choir_bass"
    UNDER_THREE = "cfcch_kid_foot_baby_toddler_infant_nursery"
    ROCK_PREK_K = "cfcch_kid_rock_prek_and_k"
    ROCK_G1 = "cfcch_kid_rock_g1"
    ROCK_G2 = "cfcch_kid_rock_g2"
    ROCK_G3 = "cfcch_kid_rock_g3"
    ROCK_G4 = "cfcch_kid_rock_g4"
    ROCK_G5 = "cfcch_kid_rock_g5"
    AFTER_SCHOOL_TABLE_1 = "cfcch_kid_after_school_table_1"
    AFTER_SCHOOL_TABLE_2 = "cfcch_kid_after_school_table_2"
    AFTER_SCHOOL_TABLE_3 = "cfcch_kid_after_school_table_3"


ROCK_TEAM_SLUG_BY_GRADE = {
    0: TeamSlugs.ROCK_PREK_K,
    1: TeamSlugs.ROCK_G1,
    2: TeamSlugs.ROCK_G2,
    3: TeamSlugs.ROCK_G3,
    4: TeamSlugs.ROCK_G4,
    5: TeamSlugs.ROCK_G5,
}


# --------------------------------------------------------------- auth groups
class Groups:
    UNSPECIFIED = "unspecified_group"
    PARTICIPANT = "organization_participant"
    CHILDREN_COWORKER = "children_coworker"
    CHILDREN_ORGANIZER = "children_organizer"
    CONFERENCE_ORGANIZER = "conference_organizer"
    DATA_ORGANIZER = "data_organizer"
    DATA_COUNSELOR = "data_counselor"
    ROSTER_EQUIPMENTS = "roster_equipments"


# ------------------------------------------------------------- roster targets
#
# 350 people, in the four disjoint buckets the church counts itself by.
CHINESE_ADULT_COUNT = 200
ENGLISH_ADULT_COUNT = 100
YOUTH_COUNT = 25
CHILD_COUNT = 25
TOTAL_ATTENDEE_COUNT = (
    CHINESE_ADULT_COUNT + ENGLISH_ADULT_COUNT + YOUTH_COUNT + CHILD_COUNT
)

#: Chinese-congregation adults who also sit in the English service.
BILINGUAL_ATTENDER_COUNT = 10

#: Deterministic namespace, so every rebuild produces identical primary keys.
GOLDEN_UUID_NAMESPACE = "1c62c3a4-6b8f-5f0c-9a2f-6d2b7f0a1e11"

#: Weeks of Sunday-service history the dataset carries.
HISTORY_WEEKS = 8
