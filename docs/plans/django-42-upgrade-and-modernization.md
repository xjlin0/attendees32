# Django 4.2 Upgrade & System Modernization Plan

## Objective
Upgrade the core framework from Django 3.2.25 to **Django 4.2 LTS**, resolve structural technical debt (DRF basenames), and successfully implement WebAuthn (Passkeys/Biometrics) which was previously blocked by version limitations.

## Core Challenges & Solutions

### 1. Upgrade Path: Django 4.2 LTS
*   **Target**: Django 4.2.x (Long Term Support).
*   **Strategy**: In-place incremental upgrade. Jumping directly to 5.x is discouraged due to potential 3rd-party library breakages. 4.2 provides the necessary foundation for `django-allauth` WebAuthn support.
*   **Infrastructure**: Update Docker configuration (Compose V2) and Python entrypoints by referencing the latest `cookiecutter-django` templates without moving the entire business logic.

### 2. DRF Modernization: The `basename` Requirement
*   **Problem**: Newer versions of Django Rest Framework (DRF) require an explicit `basename` in `router.register()` if the ViewSet doesn't define a static `queryset`.
*   **Solution**: Audit all `urls.py` files in `occasions`, `persons`, `whereabouts`, and `users` to ensure every registration has a unique `basename`. This will be done *before* the version jump.

### 3. Model Field Modernization
*   **JSON Fields**: Transition from `django.contrib.postgres.fields.JSONField` (legacy) to the native `models.JSONField` (Django 3.0+ native).
*   **Strategy**: Perform "Metadata-only" migrations where possible. For actual data type changes, use a two-step migration process (Add new field -> Data script -> Remove old field) only *after* the framework upgrade is stable.

## Phased Implementation Plan

### Phase 1: Pre-Upgrade Cleanup (Current Environment)
1.  **DRF Audit**: Add `basename` to all `router.register` calls.
2.  **Deprecation Scrub**: Search and replace remaining `ugettext`, `ugettext_lazy`, and `url()` calls with their modern equivalents.
3.  **Dependency Alignment**: Ensure all current libraries in `base.txt` have a version that supports both 3.2 and 4.2.

### Phase 2: Dependency Jump
1.  **Python Version Check**: Confirm environment is on Python 3.10+. (Currently 3.10.12, OK).
2.  **Requirement Update**: Update `requirements/base.txt` to:
    *   `Django==4.2.x`
    *   `djangorestframework>=3.14.0`
    *   `django-allauth>=64.0.0`
3.  **Settings Adjustment**: Update `CSRF_TRUSTED_ORIGINS` and other security settings required by Django 4.x.

### Phase 3: Modern Auth Implementation
1.  **WebAuthn Support**: Re-add `fido2` to requirements.
2.  **Settings Configuration**: Enable `MFA_SUPPORTED_TYPES = ["totp", "webauthn", "recovery_codes"]`.
3.  **UI Verification**: Ensure the layout inheritance established in the previous plan works with the new `allauth` layout system.

### Phase 4: Database & Field Refactoring
1.  **Native JSONField**: Migrate legacy Postgres fields to native Django JSONFields.
2.  **Migration Cleanup**: Squash old migrations if possible to simplify the dependency graph.

## Verification & Testing
1.  **Unit Tests**: Run the 50+ new tests added in the previous session.
2.  **CI/CD**: Verify GitHub Actions pass with the new Docker image.
3.  **MFA Flow**: Manually verify TOTP and then Biometric registration.

## Production Deployment Steps
When deploying this Django 4.2 upgrade to the production environment, follow these steps strictly to ensure a safe transition:

1.  **Backup Database**: Ensure a full database snapshot is taken before proceeding.
2.  **Build the Production Stack**:
    This will install the new Python dependencies (Django 4.2.30, allauth 64.0.0, etc.) in the container.
    ```bash
    docker compose -f production.yml build
    ```
3.  **Apply Database Migrations**:
    This step is critical. Django 4.2 updates internal tables and `django-pghistory` will recreate triggers.
    ```bash
    docker compose -f production.yml run --rm django python manage.py migrate
    ```
4.  **Restart Services**:
    ```bash
    docker compose -f production.yml up -d
    ```

## Rollback Strategy
*   Maintain a `git` branch for the 3.2 baseline.
*   Database Snapshot: Ensure a full DB dump is taken before Phase 2.
*   Escape Hatch: Capability to disable `allauth.mfa` as defined in the previous security plan.
