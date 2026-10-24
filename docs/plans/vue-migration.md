# Vue 3 Migration & Progressive Enhancement Plan
*Case Study: The Multi-Date Rosters Table (`/occasions/rosters/`)*

## 1. Executive Summary
This document outlines the architectural strategy for transitioning the frontend from jQuery to **Vue 3**. We use a **Progressive Enhancement** approach, allowing modern reactive components to coexist seamlessly with legacy jQuery infrastructure (`base.js`, `utilities.js`). 

The Multi-Date Rosters feature serves as the pioneer implementation, incorporating multi-date attendance matrix views, high-performance Omni Search for attendees, dynamic new attendee onboarding (distinguishing kids vs adults), unaccompanied minor safety safeguards, and smart conditional polling with operation locks.

## 2. Architecture & Tech Stack
*   **Frontend Framework**: Vue 3 (Composition API, pinned CDN for stability).
*   **UI Library**: DevExtreme Web & Vue Components (`devextreme`).
*   **Backend**: Django 4.2+ Rest Framework (DRF), PostgreSQL with `pg_trgm`, `django-pghistory`.
*   **Integration Strategy**: Vue mounts to a target DOM container (`#app`) inside the Django template. Global utilities and legacy state flags (`window.Attendees.utilities`) are shared seamlessly between Vue and legacy modules.
*   **Template Extraction Strategy**: Complex modal views and dialogs (e.g., `+ Attendee`, Signature Pad, Omni Search candidates) are defined cleanly in Django HTML using standard HTML5 `<template id="...">` elements outside `#app`, preventing JS string pollution and separating markup from logic. JavaScript modules clone and hydrate these DOM fragments on demand.

---

## 3. Case Study: Multi-Date Rosters Table

### 3.1. UI/UX Requirements
*   **Fixed Attendee Column**: Frozen left column showing attendee display name, warning flags, and historical attendance counter: `[⚠] [info] Attendee Name (16)`.
*   **Dynamic Gathering Columns**: Horizontal scrolling matrix with columns dynamically rendered for each gathering in the selected date range.
*   **Reactive Button States**:
    *   *Default*: Green outlined `[check in]` button.
    *   *Active / Hover*: Solid fill with pending indicator.
    *   *Checked In*: Automatically reveals the `[out]` button and instantly updates local count without page reload.
    *   *Unaccompanied Minor Warning*: Displays a bright red `⚠` alert tag before the `(Info)` link if a minor checked in without guardian contact.

### 3.2. Backend Data Strategy (Constant SQL Performance)
To guarantee constant query performance (3 SQL queries) regardless of the number of attendees or gatherings, the backend uses Django's `Prefetch` with in-memory pivot transformation:
1. Target `Gathering` records queried for the specified meet and date range.
2. Filtered `Attendance` records prefetched using `Prefetch('attendance_set', ...)`.
3. Active `Attending` and `AttendingMeet` queried with prefetch attached.
4. Python in-memory transformation constructs the 2D matrix JSON payload.

---

## 4. Omni Search for Attendee Check-In & Addition

### 4.1. Search Engine Architecture (`AttendeeService.search_for_roster`)
*   **Endpoint**: `/persons/api/search_attendees_for_roster/?meet_slug={slug}&q={keyword}`
*   **Security & Permissions**:
    *   Validates user authentication and organization match.
    *   Privileged users (`can_see_all_organizational_meets_attendees() == True`) search across the entire organization.
    *   General users / volunteers are strictly restricted to attendees sharing an active `Folk` with `current_user.attendee`.
*   **Multi-Modal Query Matching**:
    1. **Phone Match**: Supports raw phone digits (e.g. matching last 4 digits `3210`) or formatted phone strings (`+1(987)654-3210`).
    2. **Multi-Word & Romanization**: Tokenizes multiple words and matches both original text and unidecoded ASCII representations (e.g., `Péng` matches `Peng`).
    3. **Chinese Character Normalization**: Integrates OpenCC to seamlessly match Simplified Chinese (`陈明恩`) with Traditional Chinese (`陳明恩`).
    4. **Fuzzy Typo Tolerance**: Leverages PostgreSQL `pg_trgm` (`TrigramSimilarity`) with similarity threshold >= 0.25 to catch minor misspellings (e.g., `Wandy` for `Wendy`).
*   **Kid Meet Cross-Relation Search**:
    *   When `meet.infos.get('kid_search_families_show_grades')` is active:
    *   Searching a parent's name or phone automatically surfaces all associated family members (children) linked via `FolkAttendee`.
*   **Safety & Status Indicators**:
    *   Phone numbers masked for general display (`***-**99`).
    *   Surfaces status: `enrolled`, `paused`, `expired`, or `not_enrolled`.
    *   `can_join` flag: strictly `False` for `paused` status (cannot be auto-added without administrative review).

---

## 5. Fast Onboarding / New Attendee Registration Workflow

When Omni Search yields zero matching candidates (or after reviewing existing candidates and confirming none match), coworkers can trigger the **Quick Onboarding Dialog** directly from the roster interface.

```
+--------------------------------------------------------------------------+
|                        Add Attendee to Roster                            |
+--------------------------------------------------------------------------+
|  Target Meet: [ Kindergarten Sunday School ▾ ]  Gathering: [ 2026-10-25 ▾ ]|
|  (Preselected to ongoing or upcoming gathering, or highlighted column)   |
|                                                                          |
|  [Step 1: Search First (Mandatory)]                                      |
|  [ Search by attendee name, phone, email, or guardian...       ] [Search] |
|  * If already in meet: shows [ Already Enrolled ] & [ Locate in Roster ] |
|  * If not found: click [ Register as New Attendee ] to open form         |
|                                                                          |
|  [Step 2: New Attendee Fast Registration Form]                           |
|  --- Attendee Information ---------------------------------------------  |
|  * First Name: [ Peter       ]   * Last Name: [ Pan         ]            |
|    First Name 2 (Chinese): [ 彼得 ] Last Name 2 (Chinese): [ 潘 ]        |
|    Gender:     [ Male / Female ▾ ]                                       |
|  * Birthday:   [ 2019 ▾ ] Year  [ 05 ▾ ] Month  [ 12 ▾ ] Day (No age)   |
|    Contact:    [ Phone ▾ ]        Number/Account: [ 510-555-0123 ]       |
|                                                                          |
|  --- Kid Meet Specifics (Mandatory if infos-grade is true) ------------- |
|  * School Grade:      [ Kindergarten (K) ▾ ]                             |
|  * Food Allergies:    [ Peanut allergy / None ▾ ]                        |
|    Medical / Insurer: [ Kaiser Permanente     ] (Optional)               |
|                                                                          |
|  --- Guardian Information (Kid Meet Only) ------------------------------ |
|  [ ] Neighborhood child arrived alone / Unaccompanied minor             |
|  * Guardian Division: [ Children Division ▾ ] (Auto-selected if 1 div)   |
|  * Guardian First:    [ Mary        ]   * Guardian Last: [ Pan         ] |
|    Guardian Chinese:  [ 瑪麗        ]     Guardian Chinese: [ 潘       ] |
|  * Relationship:      [ Parent ▾    ]                                    |
|  * Contact Phone:     [ 510-555-0199]     Email: [ mary@pan.org        ] |
|                                                                          |
|                          [ Register & Check In ]                         |
+--------------------------------------------------------------------------+
```

### 5.1. Meet & Division Metadata Inspection (`show_attendee_infos`)
*   **API Modification**:
    *   Update `MeetSerializer` to serialize `show_attendee_infos` directly from `assembly.division.infos.get("show_attendee_infos", {})`.
    *   Update `OrganizationMeetsViewSet.get_queryset()` to `select_related('assembly__division')` for single-query retrieval.
*   **Zero-Roundtrip Client Inspection**:
    *   Since meets are preloaded into `lookupsCache.meets` / `meetsMap`, the frontend reads:
        ```javascript
        const meet = meetsMap.get(selectedMeetId);
        const showInfos = meet?.show_attendee_infos || {};
        const isKidMeet = Boolean(showInfos['infos-grade'] || showInfos['grade']);
        const showInsurer = Boolean(showInfos['infos-insurer'] || showInfos['insurer']);
        ```

### 5.2. Birthday Field Rules (Kids vs Adults)
*   **Strict Separation**: The UI provides distinct inputs for **Year**, **Month**, and **Day**. The system **never asks for "age"** directly to eliminate cultural confusion (nominal age vs actual age).
*   **Kids (`isKidMeet == true`)**:
    *   Year, Month, and Day are **strictly mandatory**.
    *   Validated and formatted into `YYYY-MM-DD` and saved to `attendee.actual_birthday`.
*   **Adults (`isKidMeet == false`)**:
    *   Optional or partial input allowed.
    *   If Year, Month, Day are all provided -> saved to `attendee.actual_birthday`.
    *   If Year is missing but Month & Day are provided (yearless birthday) -> stored in `attendee.estimated_birthday` with year set to `1800` (e.g., `1800-08-15`).
    *   If Year is provided without complete day -> stored in `attendee.estimated_birthday` (e.g., `1965` or `1965-08`).

### 5.3. Kid-Specific Mandatory Fields
When `isKidMeet` is true:
1.  **School Grade (`grade`)**: **Required**. Options populate from `organization.infos["grade_converter"]`. Saved to `attendee.infos["fixed"]["grade"]`.
2.  **Food Preference / Allergies (`food_pref`)**: **Required**. Users enter allergies or select "None". Saved to `attendee.infos["fixed"]["food_pref"]`.
3.  **Medical Insurance (`insurer`)**: **Optional**. Displayed only if `showInsurer == true`. Saved to `attendee.infos["fixed"]["insurer"]`.

### 5.4. Guardian Handling & Family Association
*   **Complete Family Unit Creation**:
    *   Collects guardian's English names (`first_name`, `last_name`), Chinese names (`first_name2`, `last_name2`), relationship, phone, and optional email.
    *   In a single database transaction (`transaction.atomic()`):
        1. Create Guardian `Attendee`.
        2. Create Child `Attendee`.
        3. Create `Family` `Folk` (e.g., `display_name = f"{guardian_last_name} family"`).
        4. Create two `FolkAttendee` associations linking Child and Guardian to the Family Folk.
        5. Create Child's `Attending`, `AttendingMeet`, and mark today's `Attendance` (Check-In).

### 5.5. Unaccompanied Minor Safety Protocol
*   If a neighborhood child arrives alone:
    1. Coworker checks `[✓] Child arrived alone / Unaccompanied`.
    2. Guardian fields are bypassed.
    3. Child `Attendee` is created and enrolled into `AttendingMeet`.
    4. **Safety Tagging**: Security alert stored strictly in:
       ```json
       attendingmeet.infos["special"] = {"check_in": "⚠Missing companion info"}
       ```
       *(Never stored in `Note`, preventing accidental overwrites or edits by unauthorized viewers).*
    5. **Visual Warning**: Roster DataGrid column 1 (`Attendee`) displays a red `⚠` icon before `(Info)`.
    6. **Auto-Clearance**: When a parent/guardian is subsequently registered or linked to the child via `FolkAttendee`, the system automatically removes `"check_in"` from `attendingmeet.infos["special"]`, immediately clearing the warning icon.

---

## 6. Smart Conditional Polling & Mutation Locks

### 6.1. Window-Bounded Polling
To avoid unnecessary network traffic and mobile battery drain, background polling in `rosters_list_view.js` executes strictly under conditional constraints:
*   **Time Window**: Polling runs only between `[gathering.start - 15 minutes]` and `[gathering.finish + 15 minutes]`.
*   **Visibility Check**: Polling pauses if `document.hidden` is true (user switched tabs or locked device).

### 6.2. `editingEnabled` Mutation Guard
To prevent background polling refreshes (`grid.refresh()`) from wiping out user input, `Attendees.utilities.editingEnabled` is managed as an execution mutex:
*   Set to `true` during:
    1. Signature pad popup display (`signaturePopupInstance.onShown`).
    2. AttendingMeet details editing popup (`popupInstance.onShowing`).
    3. Quick Onboarding / Add Attendee modal display.
    4. Active roll-call check-in / check-out API calls.
*   Reset to `false` upon modal dismiss, signature save/cancel, or API completion.
*   Background timer inspects `Attendees.utilities.editingEnabled`; if `true`, the scheduled polling cycle is skipped cleanly.

---

## 7. Implementation Roadmap & Checklist

### Phase 1: Backend Meet & Division API Enhancements
- [ ] In `attendees/occasions/serializers/meet.py`, add `show_attendee_infos` to `MeetSerializer`.
- [ ] In `attendees/occasions/views/api/organization_meets.py`, optimize query with `.select_related('assembly__division')`.
- [ ] Verify test coverage for `show_attendee_infos` serialization.

### Phase 2: Fast Onboarding Backend Service & Endpoint
- [ ] In `attendees/persons/services/attendee_service.py`, implement `fast_onboard_attendee`:
  - Atomic creation of Child Attendee + Optional Parent Attendee + Family Folk + FolkAttendees.
  - Strict Y/M/D handling: `actual_birthday` vs `estimated_birthday` (1800 yearless convention).
  - Grade, food allergy, and insurance storage in `infos["fixed"]`.
  - Unaccompanied minor safety tag in `attendingmeet.infos["special"]["check_in"]`.
  - Immediate `AttendingMeet` and `Attendance` generation.
- [ ] Implement auto-clearance of `attendingmeet.infos["special"]["check_in"]` upon parent linking in `FolkAttendee.save()`.
- [ ] Expose endpoint `POST /persons/api/fast_onboard_attendee/` in `attendees/persons/views/api/`.
- [ ] Write unit tests in `attendees/persons/tests/test_fast_onboard_attendee.py`.

### Phase 3: Frontend Roster Polling & Editing Guard
- [ ] In `attendees/static/js/occasions/rosters_list_view.js`:
  - Hook `Attendees.utilities.editingEnabled = true` to `signaturePopupInstance` and `attendingmeetsPopupInstance`.
  - Implement time-bounded conditional polling (`gathering.start - 15m` to `gathering.finish + 15m`, paused on `document.hidden`).
  - Add red `⚠` badge in Attendee column when `attendingmeet.infos?.special?.check_in` is detected.

### Phase 4: Frontend Quick Onboarding UI
- [ ] In `rosters_list_view.js`, add "+ Attendee" toolbar button opening the search & registration popup.
- [ ] Connect search input to `/persons/api/search_attendees_for_roster/`.
- [ ] If candidate found -> one-click check-in.
- [ ] If no candidate found -> render Fast Onboarding form:
  - Dynamically toggle Kid fields (`grade`, `food_pref`, `insurer`) using `currentMeet.show_attendee_infos`.
  - Render Y/M/D date selectors.
  - Render Guardian fields + "Unaccompanied minor" checkbox.
  - POST to fast onboarding endpoint and inject new row directly into DataGrid without full reload.
