#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main() -> None:
    # Ensure the project root is on sys.path so `pathfinder` imports resolve.
    BASE_DIR = Path(__file__).resolve().parent
    sys.path.append(str(BASE_DIR.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pathfinder.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
