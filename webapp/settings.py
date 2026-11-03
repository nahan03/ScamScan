"""Django settings. Secrets and deployment values come only from environment variables (NFR-5).

DJANGO_DEBUG=1             local development (a throwaway secret key is allowed)
DJANGO_SECRET_KEY          required when DJANGO_DEBUG is off
DJANGO_ALLOWED_HOSTS       comma-separated host names, for example "scamscan.onrender.com"
ANTHROPIC_API_KEY          optional: turns on the Claude explanation
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set the DJANGO_SECRET_KEY environment variable.")
    SECRET_KEY = "dev-only-not-a-secret"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):  # set automatically by Render
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

INSTALLED_APPS = ["checker"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "webapp.urls"
WSGI_APPLICATION = "webapp.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csp",
            ],
        },
    }
]

# No database: ads and results are never stored (NFR-2).
DATABASES = {}

# Reject oversized request bodies long before the 8,000-character check runs.
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024

# Only our own page may load; inline styles and scripts must carry the per-request nonce.
SECURE_CSP = {
    "default-src": [CSP.NONE],
    "style-src": [CSP.SELF, CSP.NONCE],
    "script-src": [CSP.SELF, CSP.NONCE],
    "form-action": [CSP.SELF],
    "base-uri": [CSP.NONE],
    "frame-ancestors": [CSP.NONE],
}

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # behind Render's proxy
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]  # the host's health check calls this over plain HTTP
    # Start small: a wrong HSTS value is hard to undo. Raise it once HTTPS is confirmed working.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "3600"))

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
