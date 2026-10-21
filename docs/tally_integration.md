# Connecting Tally

[Tally](https://github.com/vrwarp/tally) is a check-in app for a youth
ministry. It can use this Attendees server as its **people backend**: the
system of record for who its students are. Tally reads the roster's person
data from here, creates quick-added visitors as attendees, writes profile
edits back, files parents into families, and imports attendance history —
all over the JSON API, as a server-to-server client with a DRF token.

Attendance itself stays in Tally: under the current integration scope,
check-ins made in Tally are **not** written back here. History flows the
other way only (Attendees ➜ Tally, as a one-time import).

## Provisioning

One idempotent management command creates everything the integration needs
inside an existing organization:

```bash
python manage.py loaddata fixtures/db_seed.json   # once, if the vocabulary is not loaded
python manage.py setup_tally_integration --organization-slug <your-org-slug>
```

It creates, or finds if they already exist:

| Piece | Default | Why |
|---|---|---|
| Division | `<org>_tally_youth` | The division created attendees are filed under. |
| Assembly | `<org>_tally_youth_ministry` | Namespace for the meet and character. |
| Character | `<org>_tally_student` | The role a created student is enrolled as. |
| Meet | `<org>_tally_gathering` | The series a created student is enrolled in. |
| Auth group | `tally_integration` | Granted to the integration user; its name is added to the organization's `groups_see_all_meets_attendees` and `counselor` lists, which is what allows editing attendees and reading the relation vocabulary. |
| User + attendee | `tally-integration` | The API caller. The linked attendee exists because `privileged_to_edit` walks `user.attendee.under_same_org_with(...)`. |
| DRF token | — | Printed at the end. This is the `A32_TOKEN` value in Tally. |

Every slug is overridable (`--division-slug`, `--meet-slug`, …) — point them
at existing records to reuse a division or meet you already have. The command
never moves anything between organizations; it errors instead.

The command's final output is exactly the values Tally's configuration wants
(`A32_API_BASE_URL`, `A32_TOKEN`, `A32_DIVISION_ID`, `A32_MEET_SLUG`,
`A32_CHARACTER_SLUG`, `A32_ASSEMBLY_SLUG`).

## What Tally calls

All under token auth (`Authorization: Token …`), all JSON:

| Endpoint | Used for |
|---|---|
| `GET /persons/api/datagrid_data_attendee/?take&skip` | The roster sweep (the whole org, paginated). |
| `GET /persons/api/datagrid_data_attendee/?searchValue=` | Person search. |
| `GET/POST/PATCH /persons/api/datagrid_data_attendee/[{uuid}/]` | Person read, visitor create, profile edit. |
| `GET/POST /persons/api/attendee_families/` | A student's family folks; creating one for a new parent. |
| `GET/POST /persons/api/datagrid_data_familyattendees/` | Family membership edges. |
| `GET /persons/api/attendee_attendings/` | Resolving a student's attending id. |
| `PUT /persons/api/default_attendingmeets/` | Enrolling in / leaving the Tally meet. |
| `GET /persons/api/all_relations/` | The relation vocabulary (`child`, `parent`). |
| `GET /occasions/api/organization_meets/?assemblies[]=<id>` | The history-import picker. |
| `GET /occasions/api/organization_team_gatherings/?meets[]=<slug>` | Gatherings of a meet, for history import. |
| `GET /occasions/api/organization_meet_character_attendances/?meets[]=<slug>` | Attendance rows, for history import. |

## What changed on this server to make that possible

- The viewsets above used to be wrapped in Django's `login_required` /
  `LoginRequiredMixin`, which runs **before** DRF authentication — a request
  carrying a valid token was still anonymous when checked, and got a 302 to
  the login page. Those wrappers are gone; DRF's global
  `IsAuthenticated` (session **or** token) is the gate now, and the three
  viewsets that carried `SpyGuard` carry `DrfSpyGuard`
  (`attendees/users/authorization/drf_guards.py`) — the same rules, run
  after authentication, without the 2-second tarpit.
  Browser sessions behave as before; a logged-out XHR now gets a 401/403
  JSON instead of a redirect.
- A bare `GET /persons/api/datagrid_data_attendee/` (no pk, no
  `searchValue`) used to raise `UnboundLocalError` (HTTP 500). It now
  returns the caller's whole organization, ordered by id and paginated —
  which is the sweep Tally's roster read is built on.

Covered by `attendees/persons/tests/test_tally_integration.py`.
