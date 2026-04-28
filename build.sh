#!/usr/bin/env bash
set -o errexit

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate
