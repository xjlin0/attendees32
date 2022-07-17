import private_storage.urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from django.views.static import serve
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    re_path("^private-media/", include(private_storage.urls)),
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("attendees.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("summernote/", include("django_summernote.urls")),
    path(
        "occasions/",
        include(
            "attendees.occasions.urls",
            namespace="occasions",
        ),
    ),
    path(
        "whereabouts/",
        include(
            "attendees.whereabouts.urls",
            namespace="whereabouts",
        ),
    ),
    path(
        "persons/",
        include(
            "attendees.persons.urls",
            namespace="persons",
        ),
    ),
    path("api/", include("config.api_router")),  # API base url
    path("auth-token/", obtain_auth_token),      # DRF auth token
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path(
        "humans.txt",
        TemplateView.as_view(template_name="humans.txt", content_type="text/plain"),
    ),
    path(
        "ads.txt",
        TemplateView.as_view(template_name="ads.txt", content_type="text/plain"),
    ),
    re_path(
        r"[^\.](.*)(\.jsp|\.php|\.cgi|log_upload_wsgi.py|admin/controller)(.*)",
        TemplateView.as_view(template_name="404.txt", content_type="text/plain"),
    ),
    re_path(
        r"^(console|login|script|jenkins/login|files|images|uploads|\.local|\.production|\.env|\.remote|\.git|favicon.ico|feed|sitemap.xml|arttype|webfig|invoker\/readonly|solr)/?$",  # no preceding strings
        TemplateView.as_view(template_name="404.txt", content_type="text/plain"),
    ),
    re_path(
        "^:443:.*$",
        TemplateView.as_view(template_name="404.txt", content_type="text/plain"),
    ),
    re_path(  # Todo 20220702  check if this break django-allauth community login
        "^(showLogin.cc|main|logupload|var|manager/html|oauth/token|Config/SaveUploadedHotspotLogoFileConfig/SaveUploadedHotspotLogoFile|webadmin/out|HNAP1/|_ignition/execute-solution|Autodiscover/Autodiscover.xml|actuator/gateway/routes|admin/controller/extension)",
        TemplateView.as_view(template_name="404.txt", content_type="text/plain"),
    ),
    re_path(
        "^.*(/services/LogService|/j_security_check|category/latestnews/comments/feed|sites/default/files|wp-admin/css|gb)/?$",  # allow preceding strings
        TemplateView.as_view(template_name="404.txt", content_type="text/plain"),
    ),
]
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()

# API URLS
# urlpatterns += [
#     # API base url
#     path("api/", include("config.api_router")),
#     # DRF auth token
#     path("auth-token/", obtain_auth_token),
# ]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
