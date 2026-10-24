# Connecting Tally

[Tally](https://github.com/vrwarp/tally) is a church ministry check-in app.
It can use this Attendees server as its **people backend**: the system of
record for who its people are. Tally reads the roster's person data from
here, creates quick-added visitors as attendees, writes profile
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
| Division | `<org>_tally` | Where the people Tally pushes are filed, made if absent: a division of Tally's own, so what came in from Tally is easy to tell apart and triage. `--division-slug` names an existing division instead. |
| Auth group | `tally_integration` | Granted to the integration user; its name is added to the organization's `groups_see_all_meets_attendees` and `counselor` lists, which is what allows editing attendees and reading the relation vocabulary. |
| User + attendee | `tally-integration` | The API caller. The linked attendee exists because `privileged_to_edit` walks `user.attendee.under_same_org_with(...)`. |
| DRF token | — | Printed at the end. This is the `A32_TOKEN` value in Tally. |

Tally files nobody into a meet, so no assembly, meet or character is created.
The one thing it does with meets is read their history, and a meet is readable
to the token only when the group's name is in that meet's allowed groups.
`--readable-meet <slug>` grants that on an existing meet of the organization
(repeat it for several); a slug that does not exist stops the run before
anything is made. The same grant can be made later from the meet's own
settings, like for any other group.

The command never moves anything between organizations; it errors instead.
Its final output is exactly the values Tally's configuration wants
(`A32_API_BASE_URL`, `A32_TOKEN`, `A32_DIVISION_ID`). What the run was given
is kept on the integration's own attendee, under `infos["tally"]`, so the
backup and delete commands can tell what the setup made from what it found.

## What Tally calls

All under token auth (`Authorization: Token …`), all JSON:

| Endpoint | Used for |
|---|---|
| `GET /persons/api/datagrid_data_attendee/?take&skip` | The roster sweep (the whole org, paginated). |
| `GET /persons/api/datagrid_data_attendee/?searchValue=` | Person search. |
| `GET/POST/PATCH /persons/api/datagrid_data_attendee/[{uuid}/]` | Person read, visitor create, profile edit. |
| `GET/POST /persons/api/attendee_families/` | A person's family folks; creating one for a new parent. |
| `GET/POST /persons/api/datagrid_data_familyattendees/` | Family membership edges. |
| `GET /persons/api/attendee_attendings/` | Resolving a person's attending id. |
| `GET /persons/api/all_relations/` | The relation vocabulary (`child`, `parent`). |
| `GET /occasions/api/organization_meets/` | The history-import picker: the meets the group may read. |
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
