from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from sis.authz import ROLE_FINANCE, ROLE_LECTURER, ROLE_REGISTRY, ROLE_STUDENT
from sis.models import Course, Enrollment, FeeInvoice, Result, StudentProfile


class Command(BaseCommand):
    help = "Seed demo users/roles and sample data."

    def handle(self, *args, **options):
        # Groups
        registry_g, _ = Group.objects.get_or_create(name=ROLE_REGISTRY)
        finance_g, _ = Group.objects.get_or_create(name=ROLE_FINANCE)
        lecturer_g, _ = Group.objects.get_or_create(name=ROLE_LECTURER)
        student_g, _ = Group.objects.get_or_create(name=ROLE_STUDENT)

        # Users
        admin, _ = User.objects.get_or_create(username="admin", defaults={"is_superuser": True, "is_staff": True})
        if not admin.check_password("admin1234!"):
            admin.set_password("admin1234!")
        admin.is_superuser = True
        admin.is_staff = True
        admin.save()

        def mk_user(username: str, password: str, group: Group):
            u, created = User.objects.get_or_create(username=username)
            if created or not u.check_password(password):
                u.set_password(password)
            u.is_staff = True
            u.save()
            group.user_set.add(u)
            return u

        registry = mk_user("registry", "registry1234!", registry_g)
        finance = mk_user("finance", "finance1234!", finance_g)
        lecturer = mk_user("lecturer", "lecturer1234!", lecturer_g)

        # Student account + profile
        student_user, _ = User.objects.get_or_create(username="student1")
        if not student_user.check_password("student1234!"):
            student_user.set_password("student1234!")
        student_user.is_staff = False
        student_user.is_active = True
        student_user.save()
        student_g.user_set.add(student_user)

        profile, _ = StudentProfile.objects.get_or_create(
            user=student_user,
            defaults={
                "student_id": "STU-0001",
                "phone": "0000000000",
                "address": "Demo address",
                "is_verified": True,
                "verified_by": admin,
            },
        )
        if not profile.is_verified:
            profile.is_verified = True
            profile.verified_by = admin
            profile.save(update_fields=["is_verified", "verified_by"])

        # Courses
        c1, _ = Course.objects.get_or_create(
            code="CSC101",
            defaults={"title": "Introduction to Computing", "credit_units": 3, "lecturer": lecturer},
        )
        c2, _ = Course.objects.get_or_create(
            code="MTH101",
            defaults={"title": "Calculus I", "credit_units": 3, "lecturer": lecturer},
        )

        # Enrollment
        e1, _ = Enrollment.objects.get_or_create(student=profile, course=c1, year=2026, semester=1)
        Enrollment.objects.get_or_create(student=profile, course=c2, year=2026, semester=1)

        # Invoice
        FeeInvoice.objects.get_or_create(
            student=profile,
            year=2026,
            term="Tuition",
            defaults={"amount_due": "1500.00"},
        )

        # Result (one sample)
        Result.objects.get_or_create(
            enrollment=e1,
            defaults={"ca_score": "28.00", "exam_score": "40.00", "recorded_by": lecturer},
        )

        self.stdout.write(self.style.SUCCESS("Seeded demo users and sample data."))

