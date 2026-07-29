#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def _load_dotenv():
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    """Run administrative tasks."""
    _load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faircredit.settings")

    argv = sys.argv[:]
    port = os.environ.get("DJANGO_PORT")
    if port and len(argv) >= 2 and argv[1] == "runserver":
        # Only inject the port if the user didn't pass an addr:port already.
        if not any(a[:1].isdigit() or ":" in a for a in argv[2:]):
            argv.append(port)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
