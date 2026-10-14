# Golden test data: a 350-member Chinese church

`fixtures/db_seed.json` gives the application its *vocabulary* — organizations,
divisions, categories, relations, assemblies, meets, characters, teams, menus
and auth groups — plus nineteen demo people to illustrate it. The golden
dataset keeps the vocabulary, replaces the nineteen, and puts a whole
congregation inside it, so that a count is a count and a report has something
to print.

```
python manage.py load_golden_data --seed
```

```python
def test_something(golden):                 # pytest fixture, see below
    grace = golden.attendee("chen_grace")
```

## The congregation

| bucket | count | division |
| --- | --- | --- |
| Chinese immigrant adults | 200 | 中文部 (`cfcch_chinese_ministry`) |
| English-congregation adults | 100 | The Crossing (`cfcch_crossing_ministry`) |
| Youth, grades 6–12 | 25 | The Crossing |
| Children, nursery–grade 5 | 25 | Junior Ministry (`cfcch_children_ministry`) |
| **total on the roster** | **350** | |
| a household that moved away | 3 | soft-deleted, outside the 350 |

Ten of the Chinese-congregation adults also sit in the English service and hold
a participation in both.

151 family folks, plus carpool and "other relationship" folks that cut across
them. Every family has a street address in the East Bay; a few people also
carry a personal address (a college dorm, a mailing address).

## Where the shape came from

The distributions are modelled on a real church's membership export:

| in the export | in the golden data |
| --- | --- |
| `child` true for ~1/3 of rows | 50 of 350 are youth or children |
| `status` inactive for ~14% | ~14% of participations are category *Inactive* |
| `membership`: Full Member / Regular Attendee / Visitor / null | Pasts of category *member* / *receive* / *visitor* / none |
| `grade` from −1 (pre-K) to 12 | `infos.fixed.school_grade`, mapped into the organization's `grade_converter` |
| `birthdate` 1885-01-01 as "unknown" | `estimated_birthday` of `1800`, this codebase's placeholder |
| `name` that is not first + last | `first_name`/`last_name` romanised plus `last_name2`/`first_name2` in Han characters, with `infos.names` derived |
| the same person found under two spellings | 陳 appears as both *Chen* and *Chan*; 黃 as *Huang* and *Wong* |
| `medical_notes`, `nickname` | `infos.fixed.medical`, `infos.fixed.nick_name` |

Names repeat on purpose — several people are called Ruian, two children share
the given name 明恩. Tests that need to identify one person use their id, and
the search tests rely on the collisions.

## Sixteen households written by hand

A generator will not produce the shapes a church actually has to cope with, so
these are written out one by one. Each is reachable by key, e.g.
`golden.folk("HH_CHEN_THREE_GEN")`.

| key | what it exercises |
| --- | --- |
| `HH_CHEN_THREE_GEN` | three generations; the grandmother died four years ago and keeps a `deathday` and a finished folk membership |
| `HH_LIU_SINGLE_MOTHER` / `HH_LIU_EX_HUSBAND` | a divorce: children with the mother, the father in his own household, an *ex spouse* folk spanning both |
| `HH_WONG_BLENDED` | remarriage: a son, a step-daughter, a shared baby, and a half-sibling folk |
| `HH_XU_GUARDIAN` | a parachute student — a *ward*, not a son; his guardians are his emergency contacts and schedulers |
| `HH_WANG_WIDOW` | a widow living alone, birth year unknown, mobility 3, driven to church by a deacon |
| `HH_MIXED_MARRIAGE` | husband in 中文部, wife in The Crossing, child in Junior Ministry |
| `HH_GUO_FOUR_GEN` | four generations down the female line, eldest 94 with a year-and-month birthday |
| `HH_ZHANG_PASTOR` | the pastor's family; one adult child on the worship team, one away at college with a *paused* participation |
| `HH_NEW_IMMIGRANT` | arrived five months ago, all visitors, not in the printed directory |
| `HH_GRAD_ROOMMATES` | three graduate students, each their own family of one, sharing a non-family folk |
| `HH_FOSTER_CARE` | a caregiver/care-receiver placement; the birth mother attends separately and is inactive |
| `HH_TSAI_RESTAURANT` | restaurant workers: no email at all, a weekday fellowship, children in the after-school club |
| `HH_LEE_ABC` | second-generation family, English congregation throughout |
| `HH_DEPARTED` | soft-deleted household that must never surface in a live query |
| `HH_CARPOOL_EAST` | a carpool folk with one driver and three riders from three different households |

## What is tracked on each person

Names (romanised, Han, and the derived `infos.names` in both scripts, because
`opencc_convert` is on for this organization) · gender · actual, year-only,
year-and-month and unknown birthdays · death dates · grade and insurer for
minors · food preferences, medical notes, mobility, nicknames · one or two
phone numbers and email addresses, or none at all · emergency contacts and
schedulers, by attendee id · baptism, believer, member, visitor, catechumen,
interested, disbeliever, coworker and deacon statuses as `Past` rows ·
education history · public, coworker and counseling notes, the confidential
ones addressed to one reader through `infos.show_secret`.

Participations cover Sunday worship in both languages, the choir by section,
adult Sunday school, all twelve Chinese fellowships, the children's programme
by grade, the after-school club, the library, and the English youth ministry —
in every AttendingMeet category the vocabulary has (scheduled, active, primary,
secondary, remote, leave, paused, inactive, confirmed).

The 2025 summer retreat has four prices, household registrations with
donations, credits and paper/online applications, panel groups, drivers and
passengers, and a few people who pulled out.

Eight weeks of Sunday history for four meets: about 2 900 attendance rows,
marked present, absent, remote or on leave, with gaps — nobody attends every
single week.

## Signals are left switched on

Half the point of the dataset is that it exercises them, so the builder creates
one side of each pair and lets the application produce the other:

* saving an `Attendee` files them into a hidden non-family folk and opens an
  `Attending`;
* saving a baptism `Past` opens the participation on 已受洗
  (`Organization.infos.settings.past_category_to_attendingmeet_meet`);
* saving a participation on 已信主 writes the matching `Past` back
  (`Meet.infos.automatic_creation.Past`);
* saving a participation on 通訊錄 flips `Folk.infos.print_directory`
  (`Meet.infos.automatic_modification.Folk`).

## Vocabulary the golden builder adds

The seed has no English youth ministry, so the builder adds an assembly
(`cfcch_crossing_youth`), its characters, two meets and three teams; characters
and a practice meet for the existing Crossing worship team; and student/teacher
characters for the Chinese Sunday school. Their primary keys start at 100, above
the seed's range.

## Logins

Eleven personas, all with the password `golden-password-1`:

| username | groups | attendee |
| --- | --- | --- |
| `golden_superuser` | *(none)* | — |
| `golden_data_organizer` | data_organizer, organization_participant | Pastor Zhang |
| `golden_counselor` | data_counselor, organization_participant | 徐建國 |
| `golden_children_organizer` | children_organizer, organization_participant | Jonathan Lee |
| `golden_children_coworker` | children_coworker, organization_participant | Joanna Lee |
| `golden_conference_organizer` | conference_organizer, organization_participant | 馬麗雲 |
| `golden_member` | organization_participant | 陳志明 |
| `golden_crossing_member` | organization_participant | Wilson Wong |
| `golden_youth` | organization_participant | Grace Chen, 15 |
| `golden_unaffiliated` | unspecified_group | — |
| `golden_outsider` | organization_participant | — (no organization) |

`golden_superuser` has no auth groups on purpose: `RouteGuard` reads groups, not
`is_superuser`, so a superuser is refused at every page — worth pinning.

Each persona also gets a verified `allauth` `EmailAddress`, because
`ACCOUNT_EMAIL_VERIFICATION` is mandatory and the browser specs sign in through
the real form.

## Running it

The dataset is deterministic. Every UUID primary key comes from `uuid5` of a
fixed namespace and a stable key, so two runs produce identical identifiers.
Dates are relative to *today*, so ages and "currently participating" windows
stay true however long the code sits.

```
python manage.py load_golden_data --seed                       # build it
python manage.py load_golden_data --seed --force               # build it again
python manage.py load_golden_data --seed --dump fixtures/golden.json
python manage.py load_golden_data --seed --manifest e2e/golden-manifest.json
```

`--dump` writes a `loaddata`-able fixture, which is how to hand the same
congregation to another service. The fixture is not committed: it is several
megabytes of derived data and the builder is the source of truth.

`--manifest` writes a small JSON map of golden key to primary key, for callers
that are not Python — the Playwright suite reads it to know which UUID belongs
to Grace Chen.

## The e2e suite

`attendees/tests/e2e/` drives the whole application against this congregation:

| module | covers |
| --- | --- |
| `test_golden_dataset.py` | the census itself, and the four signals |
| `test_route_guard.py` | every page × every persona, against the seed's permission matrix |
| `api/<app>/test_api_<endpoint>.py` | one file per API endpoint: what it returns, who may call it, writes, scoping |
| `pages/test_page_<page>.py` | one file per page: what it renders, and the per-person guard where it has one |
| `test_admin.py` | the Django admin |
| `test_models.py` | the checks that go through no endpoint: constraints, history, content types |
| `helpers.py` | constants and small helpers the files above share |

New tests for an endpoint go in that endpoint's file; a new endpoint gets a new file.

The congregation is built once per session and committed, because rebuilding it
costs about a minute. `pytest_collection_modifyitems` in `attendees/conftest.py`
therefore runs the e2e suite **last** — committed data is visible to every other
test in the session, and the unit tests create fixtures with hard-coded primary
keys that would collide — and the session fixture flushes on the way out so a
reused database is left as it was found.

```
pytest attendees/tests/e2e            # the suite alone
pytest                                # everything; e2e still runs last
```

## The browser suite

Everything above talks HTTP. That proves the routing, the guards, the
serializers and the queries — but every roster screen in this application is an
empty `<div>` server-side that DevExtreme fills over AJAX, so none of it proves
a screen works. `e2e/` is a **Playwright suite in TypeScript** that opens the
pages in **Chromium and WebKit** and waits for the grids to have rows in them.

| spec | covers |
| --- | --- |
| `e2e/navigation.spec.ts` | sign-in through the real allauth form, sign-out, the group-driven navbar, both guard refusals as a user meets them, the printed pages |
| `e2e/datagrids.spec.ts` | the DevExtreme grids: do they boot, ask the right endpoint and render the answer |
| `e2e/journeys.spec.ts` | somebody arriving with a job to do, and finishing it — the specs that write |
| `e2e/account.spec.ts` | the door: signup closed, password turnover, and a TOTP second factor enrolled and used |
| `e2e/attendance.spec.ts` | the Sunday-morning register, including the signature pad |
| `e2e/person.spec.ts` | the record-keeping a coworker does week to week |
| `e2e/scheduling.spec.ts` | the diary: what is scheduled, the batch button's guards, the calendar |
| `e2e/reports.spec.ts` | the participation list, the envelopes, the statistics, and the spreadsheet export |
| `e2e/household.spec.ts` | families, roles, wards and addresses — what the guards are built on |
| `e2e/enrolment.spec.ts` | who is enrolled in what, ending it, and the church-wide list |

The journeys are the part that catches seams, where a save succeeds but the
thing it was supposed to change does not:

| journey | ends at |
| --- | --- |
| a data admin corrects somebody's Chinese name | finding him again by the new spelling, which is the search index, not the record |
| a coworker adds a newcomer | the person on the roster, then removed again |
| a parent looks after their children | the child's week, and a stranger's child still shut |
| the office prints the directory | a paginated document with the dead and the opted-out left out |
| anybody looks somebody up | search by romanisation, open the record, read the household |

They run in path order after `datagrids.spec.ts`, so the absolute roster counts
are asserted before anything here adds a row. Each journey either writes to a
household nobody else asserts on — the Fengs — or puts back what it changed.

**One journey is one-shot**, because what it does can only be done once:
granting somebody membership (the button withdraws itself). CI builds the
congregation fresh for every job, so this never shows there; a second *local*
run of the suite wants `manage.py load_golden_data --force` first.

Some journeys are deliberately **not** driven through the browser. Marking
somebody as passed away finishes every participation and takes them off the
roster that `datagrids.spec.ts` counts exactly, so its behaviour is proved in
pytest where it rolls back, and the browser only proves the guard: the control
is dead until editing is deliberately switched on, and it says what it is about
to do. Worth knowing that the page renders Delete and Pass away even for an
ordinary member on their own record — what stops them is the API refusing, not
the button being absent.

Unlike the pytest suite it drives a *running* application, so bring one up
first — and give it the congregation:

```
docker compose -f local.yml up -d
docker compose -f local.yml run --rm django python manage.py migrate
docker compose -f local.yml run --rm django python manage.py load_golden_data \
  --seed --force --manifest e2e/golden-manifest.json

npm ci
npx playwright install --with-deps chromium webkit
npm run test:e2e             # both engines
npm run test:e2e:chromium    # one at a time
npm run test:e2e:webkit
```

`ATTENDEES_BASE_URL` overrides where the suite looks (default
`http://localhost:8008`).

Three things about the harness are worth knowing:

* **The manifest is how TypeScript knows who is who.** `--manifest` writes
  `e2e/golden-manifest.json` — golden key to primary key, plus the personas and
  their password — from the same run that loads the data, so the two cannot
  drift. It is generated, not committed; `e2e/golden.ts` fails with the command
  to run if it is missing.
* **Third-party assets are fetched once.** The pages pull DevExtreme (4 MB),
  jQuery plugins and Bootstrap from public CDNs on every load. The fixture in
  `e2e/fixtures.ts` caches each URL per worker and replays it, passing the bytes
  through unchanged so the templates' subresource-integrity hashes still have
  to check out.
* **The failed-login rate limit has to be relaxed.** `ACCOUNT_RATE_LIMITS`
  allows three failed sign-ins per IP per ten minutes, and allauth answers a
  rate-limited attempt with the same message as a wrong password — so a suite
  that signs in dozens of times from one address, and gets the password wrong
  once on purpose, locks itself out halfway through. Run the application under
  test with `DJANGO_LOGIN_FAILED_RATE_LIMIT=1000/m`; the default is unchanged
  everywhere else.

CI runs this as its own workflow, `.github/workflows/playwright.yml`, with one
job per engine — a WebKit-only layout bug should not read as "the browser tests
are broken". Both jobs upload their HTML report as an artifact.
