# Fix Vercel 500 Error After Login - COMPLETE

## Issues Identified
1. **config/wsgi.py**: `import os` appeared AFTER `os.environ.setdefault()` — caused NameError on every request
2. **SQLite on Vercel**: Filesystem is read-only except `/tmp`. db.sqlite3 bundled at build time was read-only at runtime. Login worked (reads), but session writes and group creation failed after login.
3. **vercel.json**: `outputDirectory` was invalid for Python serverless deployments

## Fixes Applied

### 1. config/wsgi.py
- Moved `import os` to BEFORE `os.environ.setdefault()`

### 2. config/settings.py  
- Added Vercel SQLite runtime copy logic: when `VERCEL` env var is set, copy `db.sqlite3` to `/tmp/db.sqlite3` on first request so writes work

### 3. vercel.json
- Removed invalid `outputDirectory` field
- Added `"VERCEL": "1"` to env so settings.py knows it's running on Vercel

### 4. build.sh
- Added `chmod 644 db.sqlite3` to ensure database is readable for runtime copy

## Next Steps
- Commit changes and redeploy to Vercel
