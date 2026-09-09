# Vue 3 Migration & Progressive Enhancement Plan
*Case Study: The Multi-Date Rosters Table (`/occasions/rosters/`)*

## 1. Executive Summary
This document outlines the architectural strategy for transitioning the frontend from jQuery to **Vue 3**. We will use a **Progressive Enhancement** approach, allowing new pages to leverage modern reactive frameworks while peacefully coexisting with the existing jQuery infrastructure (`base.js`, `utilities.js`). The new Multi-Date Rosters feature will serve as the pioneer implementation.

## 2. Architecture & Tech Stack
*   **Frontend Framework**: Vue 3 (Composition API).
*   **UI Library**: DevExtreme Vue Components (`devextreme-vue`).
*   **Backend**: Django Rest Framework (DRF).
*   **Integration Strategy**: Vue will be mounted to a specific DOM element (e.g., `<div id="rosters-app"></div>`) within the Django template. Global utilities from legacy jQuery scripts can still be accessed via the `window` object, ensuring zero disruption to existing pages.

## 3. Case Study: Multi-Date Rosters Table
The new Rosters page requires a complex, highly interactive pivot table that displays multiple attendees across multiple gatherings.

### 3.1. UI/UX Requirements
*   **Fixed Columns**: The left column containing the Attendee's name and total attendance count (e.g., `[info] Attendee A (16)`) must be frozen.
*   **Horizontal Scrolling**: The right side of the table will dynamically generate columns for each `Gathering`, allowing horizontal scrolling without losing sight of the attendee's name.
*   **Reactive Button States**: 
    *   *Default*: Green outlined `[check in]` button.
    *   *Hover/Active*: Solid green background.
    *   *Checked In*: Automatically reveals the `[out]` button and instantly increments the attendance count without a full page reload.

### 3.2. Backend Data Strategy (Overcoming the N+1 Problem)
Rendering a 2D matrix (Pivot) from normalized SQL tables (`Attendee` -> `Attendance` <- `Gathering`) can easily trigger an N+1 query explosion if not handled correctly. 

**Solution: In-Memory Pivoting with Prefetch**
To guarantee constant query performance (exactly 3 SQL queries) regardless of the number of attendees or gatherings, we will use Django's `Prefetch` object.

*Example Django ORM Code:*
```python
from django.db.models import Prefetch

# 1. Query the target Gatherings (1 SQL Query)
gatherings = Gathering.objects.filter(
    meet__slug=target_meet, 
    start__gte=start_date, 
    start__lte=end_date
).order_by('start')

# 2. Define a Prefetch to fetch ONLY relevant attendances (1 SQL Query)
# This prevents fetching years of historical attendance data for these attendees
attendance_prefetch = Prefetch(
    'attendance_set', 
    queryset=Attendance.objects.filter(gathering__in=gatherings).select_related('category'),
    to_attr='recent_attendances'
)

# 3. Query the Attendings and attach the prefetch (1 SQL Query)
attendings = Attending.objects.filter(
    meets__slug=target_meet,
    is_removed=False
).select_related('attendee').prefetch_related(attendance_prefetch)

# 4. In-Memory Pivot
# Iterate through `attendings` and their pre-fetched `recent_attendances` 
# in Python memory to construct the JSON matrix. No further DB hits occur here.
```

*Expected JSON Output Format:*
```json
{
  "columns": [
    {"dataField": "g_101", "caption": "09/01 Gathering"}
  ],
  "rows": [
    {
      "attendee_id": 1,
      "attendee_name": "Attendee A",
      "total_attendances": 16,
      "attendances": {
        "g_101": {"status": "checked_in", "id": 55}
      }
    }
  ]
}
```

## 4. Implementation Roadmap

### Phase 1: Backend API Development
*   Create `rosters_list_view.py` for the initial page load.
*   Develop the DRF endpoint (`/api/occasions/rosters/`) implementing the 3-query prefetch and in-memory pivot logic.

### Phase 2: Frontend Scaffolding
*   Create `rosters_list_view.html` extending the base template.
*   Include Vue 3 and DevExtreme Vue packages.
*   Ensure existing `base.js` and `utilities.js` load correctly alongside Vue.

### Phase 3: Vue Component & DataGrid
*   Initialize the Vue app in `rosters_list_view.js`.
*   Implement `DxDataGrid` with dynamic columns (`v-for` loop on columns).
*   Enable `fixed="true"` for the Attendee column.

### Phase 4: Reactive State & API Integration
*   Implement Custom Cell Templates for the check-in/out buttons.
*   Wire the click events to Django backend APIs (POST/PATCH to update attendance).
*   Implement **Optimistic UI Updates**: Immediately update `row.total_attendances` and button styles in Vue's state upon successful API response, bypassing jQuery DOM manipulation entirely.

## 5. Deployment & Asset Management
Since Django is traditionally a Multi-Page Application (MPA) and we are introducing Vue 3 progressively, we have three distinct strategies for loading the Vue and DevExtreme libraries in production. We recommend starting with **Strategy A** for the pilot page, and transitioning to **Strategy C** when Vue is adopted globally.

### Strategy A: Public CDN with Pinned Versions (Recommended for Pilot)
Fetch the compiled libraries directly from a global CDN (like unpkg or cdnjs) using `<script>` tags in the Django template. **Crucially, we must lock the exact version numbers in the URL** to prevent unintended upgrades from breaking the application.
*   **How**: Add `<script src="https://unpkg.com/vue@3.3.4/dist/vue.global.prod.js"></script>` to `rosters_list_view.html`. (Notice the strict `3.3.4` version pin instead of just `@3`).
*   **Pros**: Zero changes required to your Dockerfile, deployment pipeline, or static file collection. Instant setup. Guaranteed stability due to version pinning.
*   **Cons**: Relies on external networks (though CDNs have 99.99% uptime).

### Strategy B: Self-Hosted Static Files
Download the compiled `vue.global.prod.js` and DevExtreme Vue wrappers, and place them inside the `attendees/static/js/lib/` directory.
*   **How**: Serve them via Django's `collectstatic` and WhiteNoise just like your existing jQuery files.
*   **Pros**: 100% self-hosted, no external network dependencies.
*   **Cons**: Manual process to upgrade Vue or DevExtreme versions.

### Strategy C: Modern Bundler (Vite + Node.js) - Ultimate Goal
Introduce a lightweight frontend build step using Vite (e.g., via `django-vite`).
*   **How**: Install dependencies via `package.json` (`npm install vue devextreme-vue`). Update the production `Dockerfile` to install Node.js, run `npm run build`, and then run Django's `collectstatic`.
*   **Pros**: Unlocks Vue Single-File Components (`.vue` files), tree-shaking (smaller file sizes), and professional frontend tooling.
*   **Cons**: Requires modifying the CI/CD pipeline and Dockerfile to include Node.js.

## 6. Future Considerations
*   **Django 5 Compatibility**: This decoupled architecture aligns perfectly with Django 5. The backend simply serves JSON, reducing complex template rendering logic.
*   **Legacy Code Deprecation**: As more pages adopt Vue, global functions in `utilities.js` can be incrementally refactored into standard ES Modules and imported directly into Vue components.
