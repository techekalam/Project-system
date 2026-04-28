#!/usr/bin/env bash
set -o errexit

echo "Starting Django build process..."

# Create a temporary SECRET_KEY for build if not set
if [ -z "$SECRET_KEY" ]; then
  echo "Generating temporary SECRET_KEY for build..."
  export SECRET_KEY="build-temp-key-$(date +%s)"
fi

# Set BUILD_ENV so settings.py knows we are building and keeps db.sqlite3 in the root dir
export BUILD_ENV="1"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Seed demo users
echo "Seeding demo data..."
python manage.py seed_demo || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Ensure the SQLite database is readable for runtime copy to /tmp
if [ -f "db.sqlite3" ]; then
  chmod 644 db.sqlite3
  echo "Database prepared for Vercel deployment."
fi

echo "Build process completed successfully!"
