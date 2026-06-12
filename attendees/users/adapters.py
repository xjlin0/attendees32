from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.mfa.utils import is_mfa_enabled
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_login_redirect_url(self, request):
        if getattr(settings, "MFA_ENFORCED", False) and not is_mfa_enabled(request.user):
            return reverse("mfa_index")
        return super().get_login_redirect_url(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
