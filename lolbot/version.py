"""Deployed version, baked into the image at build time (APP_VERSION / APP_COMMIT)."""
import os


def version_string() -> str:
    version = os.getenv("APP_VERSION", "dev")
    commit = os.getenv("APP_COMMIT", "unknown")[:7]
    return version if commit == "unknown" else f"{version} ({commit})"
