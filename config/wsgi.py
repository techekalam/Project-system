"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Get the Django application
application = get_wsgi_application()

# Initialize Django and run migrations on first startup
def initialize():
    """Initialize Django app and run migrations if needed."""
    try:
        from django.core.management import call_command
        from django.db import connection
        
        # Check if migrations need to be run
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM django_migrations LIMIT 1
            """)
    except Exception as e:
        # If migrations table doesn't exist, run migrations
        try:
            from django.core.management import call_command
            call_command('migrate', verbosity=0, interactive=False)
            print("[Vercel] Migrations completed successfully")
        except Exception as migrate_error:
            print(f"[Vercel] Migration error: {migrate_error}")

# Run initialization
try:
    initialize()
except Exception as e:
    print(f"[Vercel] Initialization error: {e}", file=sys.stderr)

