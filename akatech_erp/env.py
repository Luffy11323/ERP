"""Tiny .env loader (no external dependency) + Radiant credentials.

Lookup order: real environment variables > .env file.
.env is searched in: $AKATECH_ENV_FILE, the app root (apps/akatech_erp/.env),
the bench root, and ~/.akatech.env. The .env file is git-ignored.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.environ.get("AKATECH_ENV_FILE"),
    os.path.join(_HERE, "..", ".env"),
    os.path.join(_HERE, "..", "..", "..", ".env"),
    os.path.expanduser("~/.akatech.env"),
]


def _load():
    for path in _CANDIDATES:
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
            return path
    return None


ENV_PATH = _load()


def require(name):
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Missing {name}. Create a .env file (see .env.example) in apps/akatech_erp/ "
            f"or set the environment variable."
        )
    return val


BASE_URL = os.environ.get("RADIANT_BASE_URL", "https://radiant-medical.frappe.cloud")
API_KEY = require("RADIANT_API_KEY")
API_SECRET = require("RADIANT_API_SECRET")
