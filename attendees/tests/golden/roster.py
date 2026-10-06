"""
The golden roster: 350 people, the households they live in, and the church
attributes attached to each of them.

Nothing in this module touches the database — it is a pure, deterministic
description that :mod:`attendees.tests.golden.builder` turns into rows.  Keeping
the description separate means a test can assert against the *intent*
("HH_CHEN_THREE_GEN has a deceased grandmother") without re-querying the ORM.

Shape of the congregation, per the church's own count:

======================  =====  ================================================
bucket                  count  division
======================  =====  ================================================
``CHINESE_ADULT``         200  中文部 — first-generation immigrants
``ENGLISH_ADULT``         100  The Crossing — the English congregation
``YOUTH``                  25  The Crossing — grades 6-12
``CHILD``                  25  Junior Ministry — nursery through grade 5
======================  =====  ================================================

Ten of the Chinese-congregation adults also sit in the English service; they
carry the ``bilingual`` tag and get an AttendingMeet on both worship meets.

Attribute distributions (membership, grade spread, active/inactive ratio, the
``child`` flag, unknown birth years, names that do not equal first+last) are
modelled on a real church's Planning Center People data:
~1/3 children, ~14% inactive, membership split across Full Member /
Regular Attendee / Visitor / none, grades -1 through 12, and the 1885-style
placeholder birthdate that this codebase spells as the year 1800.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .constants import (
    BILINGUAL_ATTENDER_COUNT,
    CHILD_COUNT,
    CHINESE_ADULT_COUNT,
    DIVISION_CHINESE,
    DIVISION_CROSSING,
    DIVISION_JUNIOR,
    ENGLISH_ADULT_COUNT,
    YOUTH_COUNT,
    Relations,
)

# --------------------------------------------------------------------- buckets
CHINESE_ADULT = "chinese_adult"
ENGLISH_ADULT = "english_adult"
YOUTH = "youth"
CHILD = "child"

BUCKET_DIVISION = {
    CHINESE_ADULT: DIVISION_CHINESE,
    ENGLISH_ADULT: DIVISION_CROSSING,
    YOUTH: DIVISION_CROSSING,
    CHILD: DIVISION_JUNIOR,
}

BUCKET_TARGETS = {
    CHINESE_ADULT: CHINESE_ADULT_COUNT,
    ENGLISH_ADULT: ENGLISH_ADULT_COUNT,
    YOUTH: YOUTH_COUNT,
    CHILD: CHILD_COUNT,
}

# ----------------------------------------------------------------------- names
#
# Romanisations deliberately mix Mandarin pinyin (Chen, Zhang, Liu) with
# Cantonese and Taiwanese spellings (Chan, Cheung, Lau, Tsai, Hsieh) — the same
# 陳 turns up as both Chen and Chan, which is exactly the search collision a
# real roster produces.
SURNAMES: Sequence[Tuple[str, str]] = (
    ("Chen", "陳"),
    ("Wang", "王"),
    ("Li", "李"),
    ("Zhang", "張"),
    ("Liu", "劉"),
    ("Yang", "楊"),
    ("Huang", "黃"),
    ("Zhao", "趙"),
    ("Wu", "吳"),
    ("Zhou", "周"),
    ("Xu", "徐"),
    ("Sun", "孫"),
    ("Ma", "馬"),
    ("Zhu", "朱"),
    ("Hu", "胡"),
    ("Guo", "郭"),
    ("He", "何"),
    ("Gao", "高"),
    ("Lin", "林"),
    ("Luo", "羅"),
    ("Zheng", "鄭"),
    ("Liang", "梁"),
    ("Xie", "謝"),
    ("Song", "宋"),
    ("Tang", "唐"),
    ("Deng", "鄧"),
    ("Han", "韓"),
    ("Feng", "馮"),
    ("Cao", "曹"),
    ("Peng", "彭"),
    ("Chan", "陳"),
    ("Wong", "黃"),
    ("Lee", "李"),
    ("Cheung", "張"),
    ("Lau", "劉"),
    ("Ng", "吳"),
    ("Tsai", "蔡"),
    ("Hsieh", "謝"),
    ("Kuo", "郭"),
    ("Yeh", "葉"),
)

MALE_CHINESE_GIVEN: Sequence[Tuple[str, str]] = (
    ("Zhiming", "志明"),
    ("Guoqiang", "國強"),
    ("Jianguo", "建國"),
    ("Wenbin", "文彬"),
    ("Yongkang", "永康"),
    ("Shengjie", "聖傑"),
    ("Jiahao", "家豪"),
    ("Weiling", "偉倫"),
    ("Zhengxiong", "正雄"),
    ("Baoshan", "寶山"),
    ("Mingde", "明德"),
    ("Xinyuan", "信源"),
    ("Chunlin", "春霖"),
    ("Ruian", "瑞安"),
    ("Zhongxin", "忠信"),
    ("Enci", "恩賜"),
    ("Guanghui", "光輝"),
    ("Jinlong", "金龍"),
    ("Yaozong", "耀宗"),
    ("Shixiang", "世祥"),
)

FEMALE_CHINESE_GIVEN: Sequence[Tuple[str, str]] = (
    ("Shufen", "淑芬"),
    ("Meiling", "美玲"),
    ("Yulan", "玉蘭"),
    ("Xiuying", "秀英"),
    ("Huifang", "惠芳"),
    ("Peiyu", "佩瑜"),
    ("Yaqin", "雅琴"),
    ("Jingwen", "靜雯"),
    ("Suzhen", "素貞"),
    ("Liyun", "麗雲"),
    ("Enhui", "恩慧"),
    ("Xinyi", "欣怡"),
    ("Chunmei", "春美"),
    ("Wanru", "婉如"),
    ("Yaling", "雅玲"),
    ("Guizhi", "桂枝"),
    ("Shuhua", "淑華"),
    ("Zhiyi", "芝儀"),
    ("Ruixue", "瑞雪"),
    ("Mingzhu", "明珠"),
)

MALE_ENGLISH_GIVEN: Sequence[str] = (
    "Daniel", "Ethan", "Jonathan", "Samuel", "Timothy", "Andrew", "Benjamin",
    "Caleb", "Nathan", "Joshua", "Matthew", "Peter", "Stephen", "Isaac",
    "Lucas", "Aaron", "Justin", "Marcus", "Eric", "Kevin",
)

FEMALE_ENGLISH_GIVEN: Sequence[str] = (
    "Grace", "Hannah", "Rachel", "Esther", "Joanna", "Priscilla", "Abigail",
    "Naomi", "Deborah", "Rebecca", "Sarah", "Michelle", "Cynthia", "Vivian",
    "Elaine", "Karen", "Tiffany", "Angela", "Serena", "Chloe",
)

MALE_CHILD_CHINESE: Sequence[str] = (
    "明恩", "以樂", "承恩", "定國", "praise", "以信", "宗翰", "君翔",
)

FEMALE_CHILD_CHINESE: Sequence[str] = (
    "恩晴", "詩涵", "以琳", "心慈", "亮潔", "喜樂", "佳恩", "安琪",
)

NICKNAMES: Sequence[str] = (
    "Ah-Ming", "Xiao-Li", "A-Hui", "Ping-Ping", "Bao-Bao", "Da-Ge", "Xiao-Bao",
    "Lao-Chen", "A-Kin", "Mei-Mei",
)

FOOD_PREFERENCES: Sequence[str] = (
    "peanut allergy",
    "vegetarian",
    "gluten free",
    "no shellfish",
    "lactose intolerant",
    "halal",
    "low sodium",
    "no pork",
)

MEDICAL_NOTES: Sequence[str] = (
    "carries an epi-pen",
    "asthma inhaler in backpack",
    "type 1 diabetes, insulin pump",
    "seizure history, see care plan",
    "hard of hearing, seat near front",
)

INSURERS: Sequence[str] = ("Kaiser", "Blue Shield", "Anthem", "Sutter", "United")

CITIES: Sequence[Tuple[str, str]] = (
    ("Hayward", "94541"),
    ("Hayward", "94544"),
    ("Castro Valley", "94546"),
    ("San Leandro", "94578"),
    ("Union City", "94587"),
    ("Fremont", "94539"),
    ("Pleasanton", "94566"),
    ("Oakland", "94605"),
    ("San Lorenzo", "94580"),
    ("Dublin", "94568"),
)

STREETS: Sequence[str] = (
    "Smalley Avenue", "Mission Boulevard", "Foothill Boulevard", "Grove Way",
    "Redwood Road", "Hesperian Boulevard", "Tennyson Road", "Jackson Street",
    "Winton Avenue", "Whipple Road", "Alvarado Niles Road", "Decoto Road",
)


def grade_index(school_grade: int) -> int:
    """Map a school grade to the organization's ``grade_converter`` index.

    ``-3..-1`` are the under-threes, ``0`` is kindergarten, ``1..12`` are G1-G12
    and ``13+`` is post-secondary.  Kindergarten as grade ``0`` and pre-K as
    ``-1`` land here unchanged.
    """
    if school_grade <= -3:
        return 0
    if school_grade == -2:
        return 1
    if school_grade == -1:
        return 3  # Preschool 1
    if school_grade == 0:
        return 5  # Kindergarten 1
    if school_grade <= 12:
        return 6 + school_grade  # G1 -> 7 ... G12 -> 18
    return min(18 + (school_grade - 12), 26)


# ------------------------------------------------------------------- dataclasses
@dataclass
class PersonSpec:
    """One human being, before they become an :class:`~persons.models.Attendee`."""

    key: str
    bucket: str
    first_name: str
    last_name: str
    gender: str  # MALE / FEMALE / UNSPECIFIED
    first_name2: str = ""
    last_name2: str = ""
    age: Optional[int] = None
    #: ``actual`` | ``year`` | ``year_month`` | ``unknown`` | ``none``
    birthday_kind: str = "actual"
    #: years ago this person died; ``None`` for the living
    died_years_ago: Optional[float] = None
    school_grade: Optional[int] = None
    mobility: int = 2
    food_pref: Optional[str] = None
    nick_name: Optional[str] = None
    medical: Optional[str] = None
    insurer: Optional[str] = None
    email_count: int = 1
    phone_count: int = 1
    tags: frozenset = frozenset()
    #: ``(category, when_years_ago, display_name)``
    pasts: Tuple[Tuple[str, Optional[float], str], ...] = ()
    #: ``(category, body, secret_to)``
    notes: Tuple[Tuple[str, str, Optional[str]], ...] = ()
    is_removed: bool = False
    division_override: Optional[int] = None

    @property
    def division(self) -> int:
        return self.division_override or BUCKET_DIVISION[self.bucket]

    def has(self, tag: str) -> bool:
        return tag in self.tags


@dataclass
class MembershipSpec:
    """A person's place inside a folk (family, carpool or other grouping)."""

    person_key: str
    role: int
    display_order: int = 1
    #: years ago the person joined the folk
    start_years_ago: Optional[float] = None
    #: years ago the person left; ``None`` means still in it
    finish_years_ago: Optional[float] = None
    show_secret_to: Tuple[str, ...] = ()


@dataclass
class FolkSpec:
    key: str
    display_name: str
    category: int
    division: int
    members: List[MembershipSpec]
    print_directory: bool = True
    #: ``(street_number, route, city, postal)`` — only families carry addresses
    address: Optional[Tuple[str, str, str, str]] = None
    display_order: int = 0
    note: str = ""
    is_removed: bool = False


@dataclass
class Roster:
    people: Dict[str, PersonSpec]
    folks: List[FolkSpec]
    #: ``{person_key: [emergency_contact_person_key, ...]}``
    emergency_contacts: Dict[str, List[str]] = field(default_factory=dict)
    #: ``{person_key: [scheduler_person_key, ...]}``
    schedulers: Dict[str, List[str]] = field(default_factory=dict)

    def bucket(self, name: str) -> List[PersonSpec]:
        return [p for p in self.people.values() if p.bucket == name and not p.is_removed]

    def tagged(self, tag: str) -> List[PersonSpec]:
        return [p for p in self.people.values() if p.has(tag)]

    def family_folks(self) -> List[FolkSpec]:
        from .constants import FolkCategory

        return [f for f in self.folks if f.category == FolkCategory.FAMILY]


# ------------------------------------------------------------------- generator
class _Cycle:
    """A deterministic, repeatable stand-in for ``random.choice``."""

    def __init__(self, items: Sequence, step: int = 1, offset: int = 0):
        self.items = list(items)
        self.step = step
        self.index = offset

    def next(self):
        value = self.items[self.index % len(self.items)]
        self.index += self.step
        return value


class RosterBuilder:
    """Accumulates people and folks while keeping the bucket totals exact."""

    def __init__(self):
        self.people: Dict[str, PersonSpec] = {}
        self.folks: List[FolkSpec] = []
        self.emergency_contacts: Dict[str, List[str]] = {}
        self.schedulers: Dict[str, List[str]] = {}
        self.remaining = dict(BUCKET_TARGETS)
        self._surname = _Cycle(SURNAMES, step=3)
        self._male_cn = _Cycle(MALE_CHINESE_GIVEN, step=3)
        self._female_cn = _Cycle(FEMALE_CHINESE_GIVEN, step=7)
        self._male_en = _Cycle(MALE_ENGLISH_GIVEN, step=3)
        self._female_en = _Cycle(FEMALE_ENGLISH_GIVEN, step=7)
        self._male_child_cn = _Cycle(MALE_CHILD_CHINESE, step=3)
        self._female_child_cn = _Cycle(FEMALE_CHILD_CHINESE, step=5)
        self._nick = _Cycle(NICKNAMES, step=3)
        self._food = _Cycle(FOOD_PREFERENCES, step=3)
        self._medical = _Cycle(MEDICAL_NOTES, step=2)
        self._insurer = _Cycle(INSURERS, step=2)
        self._city = _Cycle(CITIES, step=3)
        self._street = _Cycle(STREETS, step=5)
        self._counter = 0

    # -- helpers ----------------------------------------------------------
    def take(self, bucket: str, count: int = 1) -> bool:
        """Reserve ``count`` slots in ``bucket``; False when the bucket is dry."""
        if self.remaining.get(bucket, 0) < count:
            return False
        self.remaining[bucket] -= count
        return True

    def next_address(self) -> Tuple[str, str, str, str]:
        self._counter += 1
        city, postal = self._city.next()
        return (str(1000 + self._counter * 7), self._street.next(), city, postal)

    def add_person(self, spec: PersonSpec) -> PersonSpec:
        assert spec.key not in self.people, f"duplicate person key {spec.key}"
        self.people[spec.key] = spec
        return spec

    def add_folk(self, folk: FolkSpec) -> FolkSpec:
        self.folks.append(folk)
        return folk

    def emergency(self, person_key: str, *contacts: str):
        self.emergency_contacts.setdefault(person_key, []).extend(contacts)

    def scheduler(self, person_key: str, *schedulers: str):
        self.schedulers.setdefault(person_key, []).extend(schedulers)

    def result(self) -> Roster:
        return Roster(
            people=self.people,
            folks=self.folks,
            emergency_contacts=self.emergency_contacts,
            schedulers=self.schedulers,
        )


# --------------------------------------------------------------- hand-authored
#
# Sixteen households written by hand.  They are the awkward shapes a generator
# would never produce and the ones the church actually has to cope with: three
# generations under one roof, a widow whose husband is still on the roll with a
# death date, a parachute student whose guardians are not his parents, a
# blended family with an ex-spouse who also attends, a family that left.
#
# Every e2e assertion that needs a *named* person reaches for one of these.

HAND_AUTHORED_KEYS = (
    "HH_CHEN_THREE_GEN",
    "HH_LIU_SINGLE_MOTHER",
    "HH_LIU_EX_HUSBAND",
    "HH_WONG_BLENDED",
    "HH_XU_GUARDIAN",
    "HH_WANG_WIDOW",
    "HH_MIXED_MARRIAGE",
    "HH_GUO_FOUR_GEN",
    "HH_ZHANG_PASTOR",
    "HH_NEW_IMMIGRANT",
    "HH_GRAD_ROOMMATES",
    "HH_FOSTER_CARE",
    "HH_TSAI_RESTAURANT",
    "HH_LEE_ABC",
    "HH_DEPARTED",
    "HH_CARPOOL_EAST",
)


def _hand_authored(rb: "RosterBuilder") -> None:  # noqa: C901 - a census, not logic
    from .constants import FolkCategory

    def person(**kwargs) -> PersonSpec:
        spec = PersonSpec(**kwargs)
        if not spec.is_removed:
            assert rb.take(spec.bucket), f"bucket {spec.bucket} exhausted at {spec.key}"
        return rb.add_person(spec)

    def family(key, display_name, division, members, **kwargs) -> FolkSpec:
        return rb.add_folk(
            FolkSpec(
                key=key,
                display_name=display_name,
                category=FolkCategory.FAMILY,
                division=division,
                members=members,
                address=kwargs.pop("address", rb.next_address()),
                **kwargs,
            )
        )

    # ---------------------------------------------------------------- 1
    # 陳家 — three generations, and a grandmother who died four years ago but
    # is still on the roll (deathday set, never removed).
    person(
        key="chen_guoqiang", bucket=CHINESE_ADULT, first_name="Guoqiang",
        last_name="Chen", first_name2="國強", last_name2="陳", gender="MALE",
        age=79, birthday_kind="year", mobility=1, nick_name="Lao-Chen",
        tags=frozenset({"baptized", "member", "directory", "deacon", "fellowship_caleb"}),
        pasts=(("education_secondary", 61.0, "Taipei Municipal Jianguo High School"),),
    )
    person(
        key="chen_guizhi", bucket=CHINESE_ADULT, first_name="Guizhi",
        last_name="Chen", first_name2="桂枝", last_name2="陳", gender="FEMALE",
        age=76, birthday_kind="year", died_years_ago=4.0,
        tags=frozenset({"baptized", "member", "deceased"}),
    )
    person(
        key="chen_zhiming", bucket=CHINESE_ADULT, first_name="Zhiming",
        last_name="Chen", first_name2="志明", last_name2="陳", gender="MALE",
        age=51, email_count=2, phone_count=2,
        tags=frozenset({"baptized", "member", "directory", "coworker", "choir",
                        "sunday_school", "fellowship_ezra", "retreat", "user_member"}),
        pasts=(("education_postgraduate", 26.0, "MS, National Taiwan University"),),
    )
    person(
        key="lin_shufen", bucket=CHINESE_ADULT, first_name="Shufen",
        last_name="Lin", first_name2="淑芬", last_name2="林", gender="FEMALE",
        age=49, food_pref="vegetarian",
        tags=frozenset({"baptized", "member", "directory", "sunday_school",
                        "fellowship_sister", "retreat", "bilingual"}),
    )
    person(
        key="chen_grace", bucket=YOUTH, first_name="Grace", last_name="Chen",
        first_name2="明恩", last_name2="陳", gender="FEMALE", age=15,
        school_grade=9, insurer="Kaiser",
        tags=frozenset({"baptized", "directory", "youth_group", "youth_worship",
                        "retreat", "user_youth"}),
    )
    person(
        key="chen_joshua", bucket=CHILD, first_name="Joshua", last_name="Chen",
        first_name2="明樂", last_name2="陳", gender="MALE", age=9,
        school_grade=3, insurer="Kaiser", food_pref="peanut allergy",
        medical="carries an epi-pen",
        tags=frozenset({"the_rock", "after_school", "directory", "retreat"}),
    )
    family(
        "HH_CHEN_THREE_GEN", "陳志明家 Chen family", DIVISION_CHINESE,
        [
            MembershipSpec("chen_zhiming", Relations.HUSBAND, 0),
            MembershipSpec("lin_shufen", Relations.WIFE, 1),
            MembershipSpec("chen_grace", Relations.DAUGHTER, 2),
            MembershipSpec("chen_joshua", Relations.SON, 3),
            MembershipSpec("chen_guoqiang", Relations.FATHER, 4, start_years_ago=6.0),
            MembershipSpec("chen_guizhi", Relations.MOTHER, 5, start_years_ago=6.0,
                           finish_years_ago=4.0),
        ],
        note="three generations; grandmother deceased four years ago",
    )
    rb.emergency("chen_grace", "chen_zhiming", "lin_shufen")
    rb.emergency("chen_joshua", "chen_zhiming", "lin_shufen")
    rb.scheduler("chen_grace", "chen_zhiming", "lin_shufen")
    rb.scheduler("chen_joshua", "chen_zhiming", "lin_shufen")
    rb.emergency("chen_guoqiang", "chen_zhiming")

    # ---------------------------------------------------------------- 2 & 3
    # A divorce: mother and children in one household, the father in his own,
    # and an ex-spouse folk that spans the two.
    person(
        key="liu_meiling", bucket=CHINESE_ADULT, first_name="Meiling",
        last_name="Liu", first_name2="美玲", last_name2="劉", gender="FEMALE",
        age=44, phone_count=2,
        tags=frozenset({"baptized", "member", "directory", "fellowship_sister",
                        "sunday_school"}),
        notes=(("counseling", "Walking through the custody arrangement with the pastor.",
                "counselor"),),
    )
    person(
        key="liu_hannah", bucket=YOUTH, first_name="Hannah", last_name="Liu",
        first_name2="恩晴", last_name2="劉", gender="FEMALE", age=13,
        school_grade=7, insurer="Blue Shield",
        tags=frozenset({"believer", "youth_group", "directory"}),
    )
    person(
        key="liu_isaac", bucket=CHILD, first_name="Isaac", last_name="Liu",
        first_name2="以樂", last_name2="劉", gender="MALE", age=11,
        school_grade=5, insurer="Blue Shield",
        tags=frozenset({"the_rock", "directory", "after_school"}),
    )
    family(
        "HH_LIU_SINGLE_MOTHER", "劉美玲家 Liu family", DIVISION_CHINESE,
        [
            MembershipSpec("liu_meiling", Relations.MOTHER, 0),
            MembershipSpec("liu_hannah", Relations.DAUGHTER, 1),
            MembershipSpec("liu_isaac", Relations.SON, 2),
        ],
        note="single mother with custody of both children",
    )
    person(
        key="liu_yongkang", bucket=CHINESE_ADULT, first_name="Yongkang",
        last_name="Liu", first_name2="永康", last_name2="劉", gender="MALE",
        age=47,
        tags=frozenset({"baptized", "interested", "inactive"}),
    )
    family(
        "HH_LIU_EX_HUSBAND", "劉永康 Liu Yongkang", DIVISION_CHINESE,
        [MembershipSpec("liu_yongkang", Relations.FATHER, 0)],
        print_directory=False,
        note="father of the Liu children, attends irregularly since the divorce",
    )
    rb.add_folk(
        FolkSpec(
            key="OTHER_LIU_EX_SPOUSES", display_name="劉/劉 ex-spouses",
            category=FolkCategory.OTHER, division=DIVISION_CHINESE,
            members=[
                MembershipSpec("liu_meiling", Relations.HIDDEN, 0),
                MembershipSpec("liu_yongkang", Relations.EX_SPOUSE, 1),
            ],
            print_directory=False,
            note="the children's parents, no longer one household",
        )
    )
    rb.emergency("liu_hannah", "liu_meiling")
    rb.emergency("liu_isaac", "liu_meiling", "liu_yongkang")
    rb.scheduler("liu_hannah", "liu_meiling")
    rb.scheduler("liu_isaac", "liu_meiling")

    # ---------------------------------------------------------------- 4
    # Blended: two remarried adults, one child each from a first marriage, and
    # a baby of their own — step-siblings and half-siblings in one folk.
    person(
        key="wong_wilson", bucket=ENGLISH_ADULT, first_name="Wilson",
        last_name="Wong", first_name2="偉倫", last_name2="黃", gender="MALE",
        age=45, email_count=2,
        tags=frozenset({"baptized", "member", "directory", "english_worship",
                        "coworker", "user_crossing"}),
    )
    person(
        key="wong_rachel", bucket=ENGLISH_ADULT, first_name="Rachel",
        last_name="Wong", gender="FEMALE", age=42,
        tags=frozenset({"baptized", "member", "directory", "english_worship"}),
    )
    person(
        key="wong_marcus", bucket=YOUTH, first_name="Marcus", last_name="Wong",
        gender="MALE", age=16, school_grade=10, insurer="Anthem",
        tags=frozenset({"believer", "youth_group", "directory", "retreat"}),
    )
    person(
        key="wong_chloe", bucket=YOUTH, first_name="Chloe", last_name="Wong",
        gender="FEMALE", age=14, school_grade=8, insurer="Anthem",
        food_pref="gluten free",
        tags=frozenset({"youth_group", "directory"}),
    )
    person(
        key="wong_naomi", bucket=CHILD, first_name="Naomi", last_name="Wong",
        first_name2="喜樂", last_name2="黃", gender="FEMALE", age=3,
        school_grade=-2, insurer="Anthem",
        tags=frozenset({"little_foot", "directory"}),
    )
    family(
        "HH_WONG_BLENDED", "Wong family 黃家", DIVISION_CROSSING,
        [
            MembershipSpec("wong_wilson", Relations.HUSBAND, 0),
            MembershipSpec("wong_rachel", Relations.WIFE, 1),
            MembershipSpec("wong_marcus", Relations.SON, 2),
            MembershipSpec("wong_chloe", Relations.STEP_SISTER, 3),
            MembershipSpec("wong_naomi", Relations.DAUGHTER, 4),
        ],
        note="blended family: Marcus is Wilson's, Chloe is Rachel's, Naomi is theirs",
    )
    rb.add_folk(
        FolkSpec(
            key="OTHER_WONG_HALF_SIBLINGS", display_name="Wong half siblings",
            category=FolkCategory.OTHER, division=DIVISION_CROSSING,
            members=[
                MembershipSpec("wong_marcus", Relations.HIDDEN, 0),
                MembershipSpec("wong_naomi", Relations.HALF_SISTER, 1),
                MembershipSpec("wong_chloe", Relations.STEP_SISTER, 2),
            ],
            print_directory=False,
        )
    )
    for kid in ("wong_marcus", "wong_chloe", "wong_naomi"):
        rb.emergency(kid, "wong_wilson", "wong_rachel")
        rb.scheduler(kid, "wong_wilson", "wong_rachel")

    # ---------------------------------------------------------------- 5
    # A parachute student: parents are in Taipei and not in the system, so his
    # guardians are a couple in a different household.
    person(
        key="xu_jianguo", bucket=CHINESE_ADULT, first_name="Jianguo",
        last_name="Xu", first_name2="建國", last_name2="徐", gender="MALE",
        age=58, phone_count=2,
        tags=frozenset({"baptized", "member", "directory", "deacon",
                        "fellowship_ezra", "junior_coworker"}),
    )
    person(
        key="xu_xiuying", bucket=CHINESE_ADULT, first_name="Xiuying",
        last_name="Xu", first_name2="秀英", last_name2="徐", gender="FEMALE",
        age=56,
        tags=frozenset({"baptized", "member", "directory", "fellowship_sister",
                        "junior_coworker"}),
    )
    person(
        key="xu_kevin", bucket=YOUTH, first_name="Kevin", last_name="Xu",
        first_name2="宗翰", last_name2="徐", gender="MALE", age=17,
        school_grade=12, insurer="United", food_pref="no shellfish",
        medical="asthma inhaler in backpack",
        tags=frozenset({"catechumen", "youth_group", "directory", "retreat"}),
        notes=(("coworker", "Parents overseas; guardians sign all permission slips.",
                "coworker"),),
    )
    family(
        "HH_XU_GUARDIAN", "徐建國家 Xu family", DIVISION_CHINESE,
        [
            MembershipSpec("xu_jianguo", Relations.HUSBAND, 0),
            MembershipSpec("xu_xiuying", Relations.WIFE, 1),
            MembershipSpec("xu_kevin", Relations.WARD, 2, start_years_ago=3.0),
        ],
        note="Kevin is a ward, not a son: his parents live in Taipei",
    )
    rb.add_folk(
        FolkSpec(
            key="OTHER_XU_GUARDIANSHIP", display_name="Kevin Xu guardianship",
            category=FolkCategory.OTHER, division=DIVISION_CHINESE,
            members=[
                MembershipSpec("xu_kevin", Relations.HIDDEN, 0),
                MembershipSpec("xu_jianguo", Relations.GUARDIAN, 1),
                MembershipSpec("xu_xiuying", Relations.GUARDIAN, 2),
            ],
            print_directory=False,
        )
    )
    rb.emergency("xu_kevin", "xu_jianguo", "xu_xiuying")
    rb.scheduler("xu_kevin", "xu_jianguo", "xu_xiuying")

    # ---------------------------------------------------------------- 6
    # An elderly widow with no birth year on record — the 1800 placeholder —
    # living alone, driven to church by a deacon.
    person(
        key="wang_yulan", bucket=CHINESE_ADULT, first_name="Yulan",
        last_name="Wang", first_name2="玉蘭", last_name2="王", gender="FEMALE",
        age=None, birthday_kind="unknown", mobility=3, phone_count=1,
        email_count=0,
        tags=frozenset({"baptized", "member", "directory", "no_email",
                        "fellowship_caleb", "remote"}),
        notes=(("coworker", "Wheelchair; needs the ramp entrance and a ride each week.",
                "coworker"),),
    )
    family(
        "HH_WANG_WIDOW", "王玉蘭 Wang Yulan", DIVISION_CHINESE,
        [MembershipSpec("wang_yulan", Relations.MOTHER, 0)],
        note="widow living alone, birth year unknown",
    )
    rb.add_folk(
        FolkSpec(
            key="OTHER_WANG_CARE", display_name="王玉蘭 care",
            category=FolkCategory.OTHER, division=DIVISION_CHINESE,
            members=[
                MembershipSpec("wang_yulan", Relations.HIDDEN, 0),
                MembershipSpec("xu_jianguo", Relations.CAREGIVER, 1),
            ],
            print_directory=False,
        )
    )
    rb.emergency("wang_yulan", "xu_jianguo")
    rb.scheduler("wang_yulan", "xu_jianguo")

    # ---------------------------------------------------------------- 7
    # Mixed marriage across the two congregations: he sits in the Chinese
    # service, she in the English one, their child is in Junior Ministry.
    person(
        key="he_shengjie", bucket=CHINESE_ADULT, first_name="Shengjie",
        last_name="He", first_name2="聖傑", last_name2="何", gender="MALE",
        age=38,
        tags=frozenset({"baptized", "member", "directory", "bilingual",
                        "fellowship_youngster", "retreat"}),
    )
    person(
        key="he_michelle", bucket=ENGLISH_ADULT, first_name="Michelle",
        last_name="He", gender="FEMALE", age=36, email_count=2,
        tags=frozenset({"baptized", "member", "directory", "english_worship",
                        "junior_coworker", "retreat"}),
    )
    person(
        key="he_caleb", bucket=CHILD, first_name="Caleb", last_name="He",
        first_name2="承恩", last_name2="何", gender="MALE", age=6,
        school_grade=0, insurer="Kaiser",
        tags=frozenset({"the_rock", "directory", "retreat"}),
    )
    family(
        "HH_MIXED_MARRIAGE", "何聖傑家 He family", DIVISION_CHINESE,
        [
            MembershipSpec("he_shengjie", Relations.HUSBAND, 0),
            MembershipSpec("he_michelle", Relations.WIFE, 1),
            MembershipSpec("he_caleb", Relations.SON, 2),
        ],
        note="husband in 中文部, wife in The Crossing, child in Junior Ministry",
    )
    rb.emergency("he_caleb", "he_shengjie", "he_michelle")
    rb.scheduler("he_caleb", "he_shengjie", "he_michelle")

    # ---------------------------------------------------------------- 8
    # Four generations down the female line, the eldest with a year-and-month
    # birthday only and the youngest in the nursery.
    person(
        key="guo_mingzhu", bucket=CHINESE_ADULT, first_name="Mingzhu",
        last_name="Guo", first_name2="明珠", last_name2="郭", gender="FEMALE",
        age=94, birthday_kind="year_month", mobility=3,
        tags=frozenset({"baptized", "member", "directory", "remote", "no_email"}),
    )
    person(
        key="guo_shuhua", bucket=CHINESE_ADULT, first_name="Shuhua",
        last_name="Guo", first_name2="淑華", last_name2="郭", gender="FEMALE",
        age=70, birthday_kind="year",
        tags=frozenset({"baptized", "member", "directory", "fellowship_caleb"}),
    )
    person(
        key="guo_vivian", bucket=ENGLISH_ADULT, first_name="Vivian",
        last_name="Guo", first_name2="佩瑜", last_name2="郭", gender="FEMALE",
        age=41,
        tags=frozenset({"believer", "directory", "english_worship", "user_crossing"}),
    )
    person(
        key="guo_lucas", bucket=CHILD, first_name="Lucas", last_name="Guo",
        first_name2="以信", last_name2="郭", gender="MALE", age=2,
        school_grade=-3, insurer="Sutter",
        tags=frozenset({"little_foot", "directory"}),
    )
    family(
        "HH_GUO_FOUR_GEN", "郭家 Guo family", DIVISION_CHINESE,
        [
            MembershipSpec("guo_mingzhu", Relations.MOTHER, 0),
            MembershipSpec("guo_shuhua", Relations.DAUGHTER, 1),
            MembershipSpec("guo_vivian", Relations.GRANDDAUGHTER, 2),
            MembershipSpec("guo_lucas", Relations.SON, 3),
        ],
        note="four generations, matrilineal; Vivian is a never-married mother",
    )
    rb.emergency("guo_lucas", "guo_vivian", "guo_shuhua")
    rb.scheduler("guo_lucas", "guo_vivian")
    rb.emergency("guo_mingzhu", "guo_shuhua")

    # ---------------------------------------------------------------- 9
    # The pastor's household: one adult child on the worship team, one away at
    # college with a paused participation.
    person(
        key="zhang_zhongxin", bucket=CHINESE_ADULT, first_name="Zhongxin",
        last_name="Zhang", first_name2="忠信", last_name2="張", gender="MALE",
        age=57, email_count=2, phone_count=2,
        tags=frozenset({"baptized", "member", "directory", "deacon", "coworker",
                        "choir", "sunday_school", "retreat", "user_data_admin"}),
        pasts=(("education_postgraduate", 30.0, "MDiv, China Evangelical Seminary"),),
    )
    person(
        key="zhang_huifang", bucket=CHINESE_ADULT, first_name="Huifang",
        last_name="Zhang", first_name2="惠芳", last_name2="張", gender="FEMALE",
        age=55,
        tags=frozenset({"baptized", "member", "directory", "fellowship_sister",
                        "sunday_school", "retreat"}),
    )
    person(
        key="zhang_timothy", bucket=ENGLISH_ADULT, first_name="Timothy",
        last_name="Zhang", first_name2="定國", last_name2="張", gender="MALE",
        age=26,
        tags=frozenset({"baptized", "member", "directory", "english_worship",
                        "youth_leader", "retreat", "user_crossing"}),
    )
    person(
        key="zhang_esther", bucket=ENGLISH_ADULT, first_name="Esther",
        last_name="Zhang", gender="FEMALE", age=20,
        tags=frozenset({"baptized", "member", "directory", "paused"}),
        pasts=(("education_college", 2.0, "UC Davis"),),
    )
    family(
        "HH_ZHANG_PASTOR", "張忠信牧師家 Pastor Zhang family", DIVISION_CHINESE,
        [
            MembershipSpec("zhang_zhongxin", Relations.HUSBAND, 0),
            MembershipSpec("zhang_huifang", Relations.WIFE, 1),
            MembershipSpec("zhang_timothy", Relations.SON, 2),
            MembershipSpec("zhang_esther", Relations.DAUGHTER, 3),
        ],
        note="pastor's family; Esther is away at college so her participation is paused",
    )

    # ---------------------------------------------------------------- 10
    # Brand-new arrivals: everyone a visitor, nobody baptised, not in print.
    person(
        key="feng_ruian", bucket=CHINESE_ADULT, first_name="Ruian",
        last_name="Feng", first_name2="瑞安", last_name2="馮", gender="MALE",
        age=34, email_count=1,
        tags=frozenset({"visitor", "interested"}),
    )
    person(
        key="feng_xinyi", bucket=CHINESE_ADULT, first_name="Xinyi",
        last_name="Feng", first_name2="欣怡", last_name2="馮", gender="FEMALE",
        age=33,
        tags=frozenset({"visitor", "catechumen"}),
    )
    person(
        key="feng_angela", bucket=CHILD, first_name="Angela", last_name="Feng",
        first_name2="安琪", last_name2="馮", gender="FEMALE", age=5,
        school_grade=-1, insurer="Kaiser",
        tags=frozenset({"the_rock", "visitor"}),
    )
    family(
        "HH_NEW_IMMIGRANT", "馮瑞安家 Feng family", DIVISION_CHINESE,
        [
            MembershipSpec("feng_ruian", Relations.HUSBAND, 0, start_years_ago=0.4),
            MembershipSpec("feng_xinyi", Relations.WIFE, 1, start_years_ago=0.4),
            MembershipSpec("feng_angela", Relations.DAUGHTER, 2, start_years_ago=0.4),
        ],
        print_directory=False,
        note="arrived five months ago; still visitors",
    )
    rb.emergency("feng_angela", "feng_ruian", "feng_xinyi")
    rb.scheduler("feng_angela", "feng_ruian", "feng_xinyi")

    # ---------------------------------------------------------------- 11
    # Three graduate students sharing a flat: each is their own family of one,
    # and the flat is a non-family folk on top.
    for idx, (fkey, first, first2, surname, surname2, gender, tags) in enumerate(
        (
            ("song_wenbin", "Wenbin", "文彬", "Song", "宋", "MALE",
             {"catechumen", "fellowship_timothy", "bilingual"}),
            ("tang_enci", "Enci", "恩賜", "Tang", "唐", "MALE",
             {"baptized", "member", "fellowship_timothy", "bilingual", "library"}),
            ("deng_yaqin", "Yaqin", "雅琴", "Deng", "鄧", "FEMALE",
             {"believer", "fellowship_timothy", "bilingual", "library"}),
        )
    ):
        person(
            key=fkey, bucket=CHINESE_ADULT, first_name=first, last_name=surname,
            first_name2=first2, last_name2=surname2, gender=gender, age=25 + idx,
            tags=frozenset(tags | {"directory"}),
            pasts=(("education_college", 4.0 + idx, "Cal State East Bay"),),
        )
        family(
            f"HH_GRAD_{fkey.upper()}", f"{surname2}{first2}", DIVISION_CHINESE,
            [MembershipSpec(fkey, Relations.UNSPECIFIED, 0)],
            print_directory=False,
        )
    rb.add_folk(
        FolkSpec(
            key="HH_GRAD_ROOMMATES", display_name="Tennyson Rd graduate flat",
            category=FolkCategory.OTHER, division=DIVISION_CHINESE,
            members=[
                MembershipSpec("song_wenbin", Relations.HIDDEN, 0),
                MembershipSpec("tang_enci", Relations.NEIGHBOR, 1),
                MembershipSpec("deng_yaqin", Relations.NEIGHBOR, 2),
            ],
            print_directory=False,
            note="three graduate students sharing a flat",
        )
    )

    # ---------------------------------------------------------------- 12
    # Foster care: the child lives with a caregiver, the birth mother is on the
    # roll but inactive.
    person(
        key="ma_liyun", bucket=CHINESE_ADULT, first_name="Liyun",
        last_name="Ma", first_name2="麗雲", last_name2="馬", gender="FEMALE",
        age=48,
        tags=frozenset({"baptized", "member", "directory", "junior_coworker",
                        "fellowship_hayward_joy"}),
    )
    person(
        key="hu_daniel", bucket=CHILD, first_name="Daniel", last_name="Hu",
        first_name2="心慈", last_name2="胡", gender="MALE", age=8,
        school_grade=2, insurer="Sutter", food_pref="lactose intolerant",
        medical="seizure history, see care plan",
        tags=frozenset({"the_rock", "after_school", "directory"}),
        notes=(("counseling", "Placement review is scheduled with the county each quarter.",
                "counselor"),),
    )
    person(
        key="hu_zhiyi", bucket=CHINESE_ADULT, first_name="Zhiyi",
        last_name="Hu", first_name2="芝儀", last_name2="胡", gender="FEMALE",
        age=31,
        tags=frozenset({"interested", "inactive"}),
    )
    family(
        "HH_FOSTER_CARE", "馬麗雲家 Ma family", DIVISION_CHINESE,
        [
            MembershipSpec("ma_liyun", Relations.CAREGIVER, 0),
            MembershipSpec("hu_daniel", Relations.CARE_RECEIVER, 1, start_years_ago=1.5),
        ],
        note="foster placement; Daniel's birth mother attends separately",
    )
    family(
        "HH_HU_BIRTH_MOTHER", "胡芝儀 Hu Zhiyi", DIVISION_CHINESE,
        [MembershipSpec("hu_zhiyi", Relations.MOTHER, 0)],
        print_directory=False,
    )
    rb.add_folk(
        FolkSpec(
            key="OTHER_HU_BIRTH_FAMILY", display_name="Daniel Hu birth family",
            category=FolkCategory.OTHER, division=DIVISION_CHINESE,
            members=[
                MembershipSpec("hu_daniel", Relations.HIDDEN, 0),
                MembershipSpec("hu_zhiyi", Relations.MOTHER, 1,
                               show_secret_to=("ma_liyun",)),
            ],
            print_directory=False,
        )
    )
    rb.emergency("hu_daniel", "ma_liyun")
    rb.scheduler("hu_daniel", "ma_liyun")

    # ---------------------------------------------------------------- 13
    # Restaurant workers: Sundays are their busiest shift, so they come to a
    # weekday fellowship and their children to the after-school club.
    person(
        key="tsai_shixiang", bucket=CHINESE_ADULT, first_name="Shixiang",
        last_name="Tsai", first_name2="世祥", last_name2="蔡", gender="MALE",
        age=46, email_count=0, phone_count=1,
        tags=frozenset({"baptized", "member", "directory", "no_email",
                        "fellowship_restaurant", "leave"}),
    )
    person(
        key="tsai_chunmei", bucket=CHINESE_ADULT, first_name="Chunmei",
        last_name="Tsai", first_name2="春美", last_name2="蔡", gender="FEMALE",
        age=44, email_count=0,
        tags=frozenset({"baptized", "member", "directory", "no_email",
                        "fellowship_restaurant"}),
    )
    person(
        key="tsai_ethan", bucket=YOUTH, first_name="Ethan", last_name="Tsai",
        first_name2="君翔", last_name2="蔡", gender="MALE", age=12,
        school_grade=6, insurer="United",
        tags=frozenset({"youth_group", "after_school", "directory"}),
    )
    person(
        key="tsai_serena", bucket=CHILD, first_name="Serena", last_name="Tsai",
        first_name2="佳恩", last_name2="蔡", gender="FEMALE", age=10,
        school_grade=4, insurer="United",
        tags=frozenset({"the_rock", "after_school", "directory"}),
    )
    family(
        "HH_TSAI_RESTAURANT", "蔡世祥家 Tsai family", DIVISION_CHINESE,
        [
            MembershipSpec("tsai_shixiang", Relations.HUSBAND, 0),
            MembershipSpec("tsai_chunmei", Relations.WIFE, 1),
            MembershipSpec("tsai_ethan", Relations.SON, 2),
            MembershipSpec("tsai_serena", Relations.DAUGHTER, 3),
        ],
        note="restaurant family: no email, weekday fellowship, after-school club",
    )
    for kid in ("tsai_ethan", "tsai_serena"):
        rb.emergency(kid, "tsai_shixiang", "tsai_chunmei")
        rb.scheduler(kid, "tsai_chunmei")

    # ---------------------------------------------------------------- 14
    # American-born Chinese couple, entirely in the English congregation, with
    # a youth and two children.
    person(
        key="lee_jonathan", bucket=ENGLISH_ADULT, first_name="Jonathan",
        last_name="Lee", gender="MALE", age=43, email_count=2,
        tags=frozenset({"baptized", "member", "directory", "english_worship",
                        "youth_leader", "retreat", "user_children_organizer"}),
    )
    person(
        key="lee_joanna", bucket=ENGLISH_ADULT, first_name="Joanna",
        last_name="Lee", gender="FEMALE", age=41,
        tags=frozenset({"baptized", "member", "directory", "junior_coworker",
                        "retreat", "user_children_coworker"}),
    )
    person(
        key="lee_nathan", bucket=YOUTH, first_name="Nathan", last_name="Lee",
        gender="MALE", age=15, school_grade=9, insurer="Kaiser",
        tags=frozenset({"baptized", "youth_group", "youth_worship", "directory",
                        "retreat"}),
    )
    person(
        key="lee_abigail", bucket=CHILD, first_name="Abigail", last_name="Lee",
        gender="FEMALE", age=10, school_grade=4, insurer="Kaiser",
        tags=frozenset({"the_rock", "directory", "retreat"}),
    )
    person(
        key="lee_peter", bucket=CHILD, first_name="Peter", last_name="Lee",
        gender="MALE", age=7, school_grade=1, insurer="Kaiser",
        food_pref="no pork",
        tags=frozenset({"the_rock", "directory", "retreat"}),
    )
    family(
        "HH_LEE_ABC", "Lee family", DIVISION_CROSSING,
        [
            MembershipSpec("lee_jonathan", Relations.HUSBAND, 0),
            MembershipSpec("lee_joanna", Relations.WIFE, 1),
            MembershipSpec("lee_nathan", Relations.SON, 2),
            MembershipSpec("lee_abigail", Relations.DAUGHTER, 3),
            MembershipSpec("lee_peter", Relations.SON, 4),
        ],
        note="second-generation family, English congregation throughout",
    )
    for kid in ("lee_nathan", "lee_abigail", "lee_peter"):
        rb.emergency(kid, "lee_jonathan", "lee_joanna")
        rb.scheduler(kid, "lee_jonathan", "lee_joanna")

    # ---------------------------------------------------------------- 15
    # A family that moved away: soft-deleted, and therefore outside the 350.
    for key, first, first2, surname, surname2, gender, age, bucket in (
        ("peng_jinlong", "Jinlong", "金龍", "Peng", "彭", "MALE", 40, CHINESE_ADULT),
        ("peng_wanru", "Wanru", "婉如", "Peng", "彭", "FEMALE", 39, CHINESE_ADULT),
        ("peng_lily", "Lily", "亮潔", "Peng", "彭", "FEMALE", 9, CHILD),
    ):
        rb.add_person(
            PersonSpec(
                key=key, bucket=bucket, first_name=first, last_name=surname,
                first_name2=first2, last_name2=surname2, gender=gender, age=age,
                school_grade=3 if bucket == CHILD else None,
                tags=frozenset({"baptized", "departed"}), is_removed=True,
            )
        )
    family(
        "HH_DEPARTED", "彭金龍家 Peng family (moved to Seattle)", DIVISION_CHINESE,
        [
            MembershipSpec("peng_jinlong", Relations.HUSBAND, 0, finish_years_ago=1.0),
            MembershipSpec("peng_wanru", Relations.WIFE, 1, finish_years_ago=1.0),
            MembershipSpec("peng_lily", Relations.DAUGHTER, 2, finish_years_ago=1.0),
        ],
        print_directory=False,
        is_removed=True,
        note="soft-deleted household; must not appear in any live query",
    )

    # ---------------------------------------------------------------- 16
    # A carpool that spans three unrelated families.
    rb.add_folk(
        FolkSpec(
            key="HH_CARPOOL_EAST", display_name="Castro Valley carpool 共乘",
            category=FolkCategory.CARPOOL, division=DIVISION_CHINESE,
            members=[
                MembershipSpec("xu_jianguo", Relations.DRIVER, 0),
                MembershipSpec("wang_yulan", Relations.PASSENGER, 1),
                MembershipSpec("guo_mingzhu", Relations.PASSENGER, 2),
                MembershipSpec("guo_shuhua", Relations.PASSENGER, 3),
            ],
            print_directory=False,
            note="one driver, three riders, three different households",
        )
    )


# ------------------------------------------------------------------- generated
#
# Everything the hand-authored households did not cover, filled in until each
# bucket lands exactly on its target.  The distributions below are the ones a
# real church of this size shows.

FELLOWSHIP_TAGS = (
    "fellowship_ezra",
    "fellowship_bible_study",
    "fellowship_timothy",
    "fellowship_restaurant",
    "fellowship_sister",
    "fellowship_youngster",
    "fellowship_caleb",
    "fellowship_hayward_joy",
    "fellowship_oakland_renew",
    "fellowship_castro_valley_kind",
    "fellowship_pleasanton_faithful",
    "fellowship_fremont_confident",
)


def _adult_tags(index: int, bucket: str) -> set:
    """Church attributes for a generated adult, spread deterministically."""
    tags = set()
    slot = index % 100
    if slot < 57:
        tags |= {"baptized", "member"}
    elif slot < 72:
        tags.add("believer")
    elif slot < 84:
        tags.add("visitor")
    elif slot < 92:
        tags.add("catechumen")
    elif slot < 97:
        tags.add("interested")
    else:
        tags.add("disbeliever")

    if index % 7 == 3:  # ~14%, the inactive share the mirror reports
        tags.add("inactive")
    if index % 23 == 5:
        tags.add("paused")
    if index % 19 == 7:
        tags.add("remote")
    if index % 31 == 11:
        tags.add("leave")
    if index % 100 < 85 and "visitor" not in tags:
        tags.add("directory")
    if index % 11 == 2:
        tags.add("coworker")
    if index % 37 == 4:
        tags.add("deacon")
    if index % 10 == 6:
        tags.add("library")
    if index % 3 == 0:
        tags.add("retreat")
    if index % 13 == 9:
        tags.add("no_email")

    if bucket == CHINESE_ADULT:
        tags.add(FELLOWSHIP_TAGS[index % len(FELLOWSHIP_TAGS)])
        if index % 8 == 1:
            tags.add("choir")
        if index % 3 == 1:
            tags.add("sunday_school")
    else:
        if index % 7 == 2:
            tags.add("english_worship")
        if index % 17 == 5:
            tags.add("youth_leader")
        if index % 9 == 4:
            tags.add("junior_coworker")
    return tags


def _generated(rb: "RosterBuilder") -> None:
    from .constants import FolkCategory

    counter = {"n": 0}

    def make_adult(bucket: str, gender: str, surname, age: int, index: int,
                   key: str) -> PersonSpec:
        if bucket == CHINESE_ADULT:
            given = (rb._male_cn if gender == "MALE" else rb._female_cn).next()
            first_name, first_name2 = given
        else:
            first_name = (rb._male_en if gender == "MALE" else rb._female_en).next()
            first_name2 = (
                (rb._male_cn if gender == "MALE" else rb._female_cn).next()[1]
                if index % 5 != 0
                else ""
            )
        tags = _adult_tags(index, bucket)
        birthday_kind = "actual"
        if index % 17 == 0 and age > 60:
            birthday_kind = "year"
        elif index % 29 == 3 and age > 55:
            birthday_kind = "unknown"
        elif index % 23 == 8:
            birthday_kind = "none"
        spec = PersonSpec(
            key=key, bucket=bucket, first_name=first_name, last_name=surname[0],
            first_name2=first_name2, last_name2=surname[1] if first_name2 else "",
            gender=gender, age=age, birthday_kind=birthday_kind,
            mobility=1 if age > 75 else (3 if index % 41 == 0 else 2),
            food_pref=rb._food.next() if index % 6 == 0 else None,
            nick_name=rb._nick.next() if index % 9 == 0 else None,
            medical=rb._medical.next() if index % 47 == 0 else None,
            email_count=0 if "no_email" in tags else (2 if index % 8 == 0 else 1),
            phone_count=2 if index % 5 == 0 else 1,
            tags=frozenset(tags),
            pasts=(
                (("education_college", float(age - 22), "Cal State East Bay"),)
                if index % 4 == 0 and age > 24
                else ()
            ),
            notes=(
                (("public", "Prefers Mandarin for pastoral visits.", None),)
                if index % 12 == 0
                else ()
            ),
        )
        assert rb.take(bucket), f"bucket {bucket} exhausted at {key}"
        return rb.add_person(spec)

    def make_young(bucket: str, gender: str, surname, index: int, key: str,
                   school_grade: int) -> PersonSpec:
        age = max(1, school_grade + 6)
        if bucket == YOUTH:
            first_name = (rb._male_en if gender == "MALE" else rb._female_en).next()
        else:
            first_name = (rb._male_en if gender == "MALE" else rb._female_en).next()
        first_name2 = (
            (rb._male_child_cn if gender == "MALE" else rb._female_child_cn).next()
            if index % 4 != 0
            else ""
        )
        tags = set()
        if bucket == YOUTH:
            tags.add("youth_group")
            if index % 3 == 0:
                tags.add("baptized")
            elif index % 3 == 1:
                tags.add("believer")
            else:
                tags.add("catechumen")
            if index % 5 == 0:
                tags.add("youth_worship")
        else:
            tags.add("little_foot" if school_grade < -1 else "the_rock")
            if index % 4 == 0:
                tags.add("after_school")
            if index % 6 == 0:
                tags.add("believer")
        if index % 3 != 2:
            tags.add("directory")
        if index % 4 == 1:
            tags.add("retreat")
        if index % 9 == 3:
            tags.add("inactive")
        spec = PersonSpec(
            key=key, bucket=bucket, first_name=first_name, last_name=surname[0],
            first_name2=first_name2, last_name2=surname[1] if first_name2 else "",
            gender=gender, age=age, school_grade=school_grade,
            insurer=rb._insurer.next(),
            food_pref=rb._food.next() if index % 5 == 0 else None,
            medical=rb._medical.next() if index % 11 == 0 else None,
            tags=frozenset(tags),
        )
        assert rb.take(bucket), f"bucket {bucket} exhausted at {key}"
        return rb.add_person(spec)

    def household(members, division, surname, note="") -> FolkSpec:
        counter["n"] += 1
        n = counter["n"]
        return rb.add_folk(
            FolkSpec(
                key=f"HH_GEN_{n:03d}",
                display_name=f"{surname[1]}{surname[0]} household {n:03d}",
                category=FolkCategory.FAMILY,
                division=division,
                members=members,
                address=rb.next_address(),
                print_directory=n % 9 != 0,
                note=note,
            )
        )

    index = 0

    # 1. Households with children and/or youth, until both buckets are empty.
    while rb.remaining[CHILD] or rb.remaining[YOUTH]:
        index += 1
        surname = rb._surname.next()
        parent_bucket = ENGLISH_ADULT if index % 3 == 0 else CHINESE_ADULT
        if rb.remaining[parent_bucket] < 2:
            parent_bucket = (
                CHINESE_ADULT if rb.remaining[CHINESE_ADULT] >= 2 else ENGLISH_ADULT
            )
        if rb.remaining[parent_bucket] < 2:
            break
        division = BUCKET_DIVISION[parent_bucket]
        single_parent = index % 8 == 5
        father = None
        if not single_parent:
            father = make_adult(
                parent_bucket, "MALE", surname, 38 + (index % 12), index,
                f"gen_{index:03d}_father",
            )
        mother = make_adult(
            parent_bucket, "FEMALE", surname, 36 + (index % 12), index + 1,
            f"gen_{index:03d}_mother",
        )
        members = []
        order = 0
        if father:
            members.append(MembershipSpec(father.key, Relations.HUSBAND, order))
            order += 1
            members.append(MembershipSpec(mother.key, Relations.WIFE, order))
        else:
            members.append(MembershipSpec(mother.key, Relations.MOTHER, order))
        order += 1

        wanted_youth = min(rb.remaining[YOUTH], 2 if index % 4 == 0 else 1)
        wanted_child = min(rb.remaining[CHILD], 2 if index % 3 == 0 else 1)
        kids = []
        for k in range(wanted_youth):
            gender = "MALE" if (index + k) % 2 else "FEMALE"
            grade = 6 + ((index + k * 3) % 7)
            kid = make_young(
                YOUTH, gender, surname, index + k, f"gen_{index:03d}_youth_{k}", grade
            )
            kids.append(kid)
            members.append(
                MembershipSpec(
                    kid.key,
                    Relations.SON if gender == "MALE" else Relations.DAUGHTER,
                    order,
                )
            )
            order += 1
        for k in range(wanted_child):
            gender = "FEMALE" if (index + k) % 2 else "MALE"
            grade = ((index * 2 + k * 5) % 9) - 3
            kid = make_young(
                CHILD, gender, surname, index + k, f"gen_{index:03d}_child_{k}", grade
            )
            kids.append(kid)
            members.append(
                MembershipSpec(
                    kid.key,
                    Relations.SON if gender == "MALE" else Relations.DAUGHTER,
                    order,
                )
            )
            order += 1

        # Every fifth household has a grandparent living in.
        if index % 5 == 0 and rb.remaining[CHINESE_ADULT] >= 1:
            grandparent = make_adult(
                CHINESE_ADULT, "FEMALE" if index % 2 else "MALE", surname,
                72 + (index % 15), index + 2, f"gen_{index:03d}_grandparent",
            )
            members.append(
                MembershipSpec(
                    grandparent.key,
                    Relations.MOTHER if index % 2 else Relations.FATHER,
                    order,
                    start_years_ago=float(1 + index % 6),
                )
            )

        household(members, division, surname,
                  note="single parent" if single_parent else "")
        for kid in kids:
            contacts = [mother.key] + ([father.key] if father else [])
            rb.emergency(kid.key, *contacts)
            rb.scheduler(kid.key, *contacts)

    # 2. Adult-only households: couples first, then the singles that top off
    #    each bucket exactly.
    for bucket in (CHINESE_ADULT, ENGLISH_ADULT):
        while rb.remaining[bucket] >= 2:
            index += 1
            surname = rb._surname.next()
            base_age = 30 + (index * 7) % 50
            husband = make_adult(bucket, "MALE", surname, base_age, index,
                                 f"gen_{index:03d}_husband")
            wife = make_adult(bucket, "FEMALE", surname, base_age - 2, index + 1,
                              f"gen_{index:03d}_wife")
            household(
                [
                    MembershipSpec(husband.key, Relations.HUSBAND, 0),
                    MembershipSpec(wife.key, Relations.WIFE, 1),
                ],
                BUCKET_DIVISION[bucket],
                surname,
                note="empty nesters" if base_age > 62 else "",
            )
            rb.emergency(husband.key, wife.key)
            rb.emergency(wife.key, husband.key)

        while rb.remaining[bucket] >= 1:
            index += 1
            surname = rb._surname.next()
            gender = "MALE" if index % 2 else "FEMALE"
            single = make_adult(bucket, gender, surname, 24 + (index * 3) % 55,
                                index, f"gen_{index:03d}_single")
            household(
                [MembershipSpec(single.key, Relations.UNSPECIFIED, 0)],
                BUCKET_DIVISION[bucket],
                surname,
                note="lives alone",
            )


def build_roster() -> Roster:
    """The whole congregation, deterministically."""
    rb = RosterBuilder()
    _hand_authored(rb)
    _generated(rb)

    assert all(remaining == 0 for remaining in rb.remaining.values()), rb.remaining

    # Exactly ten Chinese-congregation adults also sit in the English service.
    bilingual = [p for p in rb.people.values() if p.has("bilingual")]
    if len(bilingual) < BILINGUAL_ATTENDER_COUNT:
        candidates = [
            p
            for p in rb.people.values()
            if p.bucket == CHINESE_ADULT
            and not p.has("bilingual")
            and not p.is_removed
            and not p.has("deceased")
            and not p.has("inactive")
        ]
        candidates.sort(key=lambda p: p.key)
        for person in candidates[: BILINGUAL_ATTENDER_COUNT - len(bilingual)]:
            person.tags = frozenset(person.tags | {"bilingual"})

    return rb.result()
