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

You can override:
- `DJANGO_EMAIL_BACKEND`
- `DJANGO_DEFAULT_FROM_EMAIL`
- `DJANGO_SITE_URL`

