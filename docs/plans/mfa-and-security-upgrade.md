# Security Hardening & MFA Implementation Plan

## Objective
Enable Multi-Factor Authentication (MFA/Google Authenticator OTP) with minimal code changes by leveraging the native MFA support in a newer version of `django-allauth`. Concurrently, address high-priority security vulnerabilities in existing dependencies (`Pillow`, `GitPython`) while maintaining compatibility with the current Django 3.2.25 environment.

## Key Files & Context
- **Dependencies**: `requirements/base.txt`
- **Django Settings**: `config/settings/base.py`
- **Database**: Requires migrations for the new `allauth.mfa` app.

## Implementation Steps

### 1. Update Dependencies (`requirements/base.txt`)
Modify the `requirements/base.txt` file to upgrade vulnerable and outdated packages to secure, Django 3.2-compatible versions:
- Change `Pillow==9.3.0` to `Pillow==9.5.0` (Addresses CVE-2023-50447, CVE-2023-44271 while avoiding `Image.ANTIALIAS` deprecation issues in v10+).
- Change `django-allauth==0.53.0` to `django-allauth==0.63.3` (Latest stable 0.x branch that officially supports Django 3.2 and includes native MFA).
- Change `GitPython==3.1.43` to `GitPython==3.1.44` (or latest compatible 3.1.x to address CVE-2024-22190).
- Add `PyJWT==2.8.0` (Required by `django-allauth` for JWT-based social login/OIDC).
- Add `cryptography==42.0.5` (Required for JWT signature verification).
- Add `qrcode[pil]==7.4.2` (Required for generating TOTP QR codes).
- Add `python-fido2==1.1.2` (Required for WebAuthn/Passkey support).

### 2. Configure Django Settings (`config/settings/base.py`)
Enable and configure the MFA application provided by `django-allauth`:
- **INSTALLED_APPS**: 
    - Add `"allauth.mfa"` to the `THIRD_PARTY_APPS`.
    - Ensure `"django.contrib.humanize"` is enabled in `DJANGO_APPS`.
- **MIDDLEWARE**: Add `"allauth.account.middleware.AccountMiddleware"` after `AuthenticationMiddleware`.
- **MFA Settings**: Update the MFA configuration block:
  ```python
  # allauth MFA Settings
  MFA_SUPPORTED_TYPES = ["totp", "webauthn", "recovery_codes"]
  MFA_PASSCODE_LENGTH = 6
  MFA_ENFORCED = env.bool("DJANGO_MFA_ENFORCED", False)
  MFA_PASSKEY_LOGIN_ENABLED = True
  MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = env.bool("DJANGO_MFA_WEBAUTHN_INSECURE", True)
  ```

### 3. URL Configuration (`config/urls.py`)
Ensure the MFA URLs are explicitly included if not automatically covered by `allauth.urls`:
```python
urlpatterns = [
    ...
    path("accounts/", include("allauth.urls")),
    path("accounts/mfa/", include("allauth.mfa.urls")),  # Add this line
    ...
]
```

### 4. Database Migration
Since a new app (`allauth.mfa`) is being added, a database migration is required to create the necessary tables for storing user TOTP secrets and recovery codes.
- Run `python manage.py migrate`.

### 4. Template Review (Optional/As Needed)
- Verify that the default MFA templates provided by `django-allauth` (e.g., `mfa/index.html`, `mfa/totp/activate.html`) integrate adequately with the existing project theme (Bootstrap 5 via `crispy-bootstrap5`).
- *Note*: If the default templates are visually inconsistent, they can be overridden in `attendees/templates/mfa/` in a subsequent UX pass.

## Verification & Testing
1. **Dependency Installation**: Run `pip install -r requirements/base.txt` and ensure no dependency resolution conflicts occur.
2. **Migration**: Run `python manage.py migrate` successfully.
3. **Application Start**: Start the development server and verify it runs without errors.
4. **MFA Flow Testing**:
   - Log in as an existing user.
   - Navigate to the MFA configuration route (usually `/accounts/mfa/` or accessible via account management).
   - Successfully setup a TOTP application (Google Authenticator) by scanning the QR code.
   - Log out.
   - Log back in, verifying that the system prompts for the 6-digit TOTP code after password validation.
   - Successfully authenticate using the TOTP code.
   - Verify that recovery codes can be generated and used to bypass TOTP if necessary.

## Migration & Rollback
- **Rollback Plan**: If critical issues arise post-deployment, revert `requirements/base.txt` and `config/settings/base.py` to their previous states. Note that rolling back `django-allauth` versions after migrations have been applied may require manual database intervention (dropping the `mfa_*` tables) if the application refuses to start with the newer schema but older code.

## Emergency Escape Hatch (Method A)
If the system is in production and users are locked out due to OTP issues, you can immediately disable the MFA requirement without breaking the database by:
1. In `config/settings/base.py`, comment out `"allauth.mfa"` from `THIRD_PARTY_APPS`.
2. Redeploy.
3. Users who have already configured MFA will no longer be prompted for OTP during login. The TOTP secrets remain in the database (until the app is re-enabled), but the authentication flow will bypass the MFA check.

## Phase 2: Making MFA Mandatory
Once the pilot phase is complete and users are familiar with the system, you can enforce MFA for all or specific users.

### 1. Global Enforcement
To require MFA for **all users** to access the system, add the following to `config/settings/base.py`:
```python
# Force MFA for everyone
# Note: Users will be redirected to the MFA setup page upon login if they haven't configured it.
# MFA_REAUTHENTICATE_TIMEOUT = 300  # Optional: prompt for OTP again after 5 mins of inactivity
# ALLAUTH_MFA_FORMS = { ... } # Optional: customize forms
```
*Note: As of django-allauth v0.63.x, global enforcement is typically handled via a custom adapter or by checking `user.is_authenticated` in conjunction with `MFA_SUPPORTED_TYPES` in your login middleware/mixins.*

### 2. Selective Enforcement (via Adapter)
To enforce MFA for specific roles (e.g., Staff only), you can modify `attendees/users/adapters.py`:
```python
from allauth.mfa.utils import is_mfa_enabled

class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.is_staff and not is_mfa_enabled(request.user):
            return reverse("mfa_index")  # Redirect to setup page
        return super().get_login_redirect_url(request)
```