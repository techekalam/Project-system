# Student Information System (Prototype)

Working prototype for:
- Student registration & profile management
- Course enrollment/management
- Tuition fee/payment tracking
- Result recording & access
- Report generation
- Secure access for different user roles (administrators, registry staff, finance staff, lecturers, students)

## Tech
- Python + Django
- SQLite (default; no setup)

## Quick start (Windows PowerShell)

```powershell
cd e:\Cursor_work
py -3.14 -m pip install -r requirements.txt
py -3.14 manage.py migrate
py -3.14 manage.py seed_demo
py -3.14 manage.py runserver
```

Open `http://127.0.0.1:8000/`

## Demo users
Created by `python manage.py seed_demo`:
- admin / admin1234! (Superuser)
- registry / registry1234!
- finance / finance1234!
- lecturer / lecturer1234!
- student1 / student1234!

## Notes
- Role permissions are implemented via Django Groups.
- Reports are simple HTML pages you can print/save as PDF in the browser.

## Student self-signup + admin approval (email verification)

- **Signup page**: `http://127.0.0.1:8000/signup/`
- When a student signs up:
  - their user is created as **inactive**
  - their profile is marked **unverified**
  - **admins are emailed** an approval link
- Admin/registry staff opens the approval link and clicks **Approve & activate**

### Email in development
By default, emails are printed to the terminal (console email backend).

## Vercel Deployment

This project is optimized for deployment on Vercel with the following features:
- Serverless Django application using Gunicorn
- WhiteNoise for static file serving
- PostgreSQL database support
- Environment-based configuration

### Prerequisites
1. Vercel account (free at https://vercel.com)
2. GitHub repository connected to Vercel
3. PostgreSQL database (use Vercel Postgres or external provider)

### Deployment Steps

1. **Clone and setup locally:**
   ```bash
   git clone https://github.com/techekalam/Project-system.git
   cd Project-system
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Create .env file with production settings:**
   - Copy `.env.example` to `.env`
   - Update with your production values:
     - `SECRET_KEY`: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
     - Database credentials
     - Email settings
     - Domain names

3. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Optimize for Vercel deployment"
   git push
   ```

4. **Deploy on Vercel:**
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Add environment variables from your `.env` file
   - Click Deploy

5. **Post-deployment:**
   - Vercel will automatically run migrations via `build.sh`
   - Collect static files with WhiteNoise
   - Access your app at the provided Vercel domain

### Environment Variables for Vercel

Set these in Vercel project settings:
- `SECRET_KEY` - Generate a new secure key
- `DEBUG` - Set to `False`
- `ALLOWED_HOSTS` - Your Vercel domain and custom domain
- `USE_POSTGRES` - Set to `True`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL credentials
- `DJANGO_EMAIL_BACKEND` - SMTP backend for emails
- `CSRF_TRUSTED_ORIGINS` - Your deployment domain(s)
- Other email settings as needed

### Database Migration

Migrations are automatically run on deployment. For manual migration:
```bash
vercel env pull
python manage.py migrate
```

### Static Files

Static files are automatically collected and compressed using WhiteNoise.
CSS, JS, and images are cached for 1 year on Vercel's CDN.

### Monitoring & Logs

View deployment logs and metrics in Vercel dashboard:
1. Go to your project dashboard
2. Click "Deployments" to see deployment history
3. Click on a deployment to view real-time logs

You can override:
- `DJANGO_EMAIL_BACKEND`
- `DJANGO_DEFAULT_FROM_EMAIL`
- `DJANGO_SITE_URL`

