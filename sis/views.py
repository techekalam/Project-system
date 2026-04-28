from __future__ import annotations

import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db import models
from django.db.models import Avg, Count, F, FloatField, Sum
from django.db.models.functions import Cast
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

from .authz import (
    ROLE_FINANCE,
    ROLE_LECTURER,
    ROLE_REGISTRY,
    ROLE_STUDENT,
    require_any_group,
    user_in_group,
)
from .forms import (
    CourseForm,
    EnrollmentForm,
    FeeInvoiceForm,
    PaymentForm,
    ResultForm,
    StudentCreateForm,
    StudentEditForm,
    StudentSelfEditForm,
    StudentSignupForm,
)
from .models import Course, Enrollment, FeeInvoice, Payment, Result, StudentProfile


def _ensure_role_groups_exist():
    try:
        for name in [ROLE_REGISTRY, ROLE_FINANCE, ROLE_LECTURER, ROLE_STUDENT]:
            Group.objects.get_or_create(name=name)
    except Exception as e:
        # Silently fail if groups can't be created (e.g., during migrations)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not create role groups: {e}")

def _verification_signer() -> TimestampSigner:
    return TimestampSigner(salt="sis.student.verify")


def _build_verify_url(request: HttpRequest, student: StudentProfile) -> str:
    token = _verification_signer().sign(str(student.pk))
    base = getattr(settings, "SITE_URL", "").rstrip("/") or (request.build_absolute_uri("/")[:-1])
    return f"{base}/signup/verify/{token}/"


def _notify_admins_for_student_verification(request: HttpRequest, student: StudentProfile) -> None:
    # Notify superusers by email. If not configured, console backend prints email in terminal.
    recipients = list(
        User.objects.filter(is_superuser=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        return
    url = _build_verify_url(request, student)
    subject = f"SIS: Approve student {student.student_id}"
    body = (
        f"A new student signed up and needs approval.\n\n"
        f"Student ID: {student.student_id}\n"
        f"Username: {student.user.username}\n"
        f"Name: {student.user.get_full_name()}\n"
        f"Email: {student.user.email}\n\n"
        f"Approve here:\n{url}\n"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


@login_required
def home(request: HttpRequest) -> HttpResponse:
    _ensure_role_groups_exist()

    roles = []
    for r in [ROLE_REGISTRY, ROLE_FINANCE, ROLE_LECTURER, ROLE_STUDENT]:
        if user_in_group(request.user, r):
            roles.append(r)
    if request.user.is_superuser and "Administrators" not in roles:
        roles.insert(0, "Administrators")

    ctx = {
        "roles": roles,
        "student_profile": getattr(request.user, "student_profile", None),
    }
    return render(request, "sis/home.html", ctx)


def signup(request: HttpRequest) -> HttpResponse:
    """
    Student self-signup.
    Creates an INACTIVE user + unverified StudentProfile, then emails admins an approval link.
    """
    _ensure_role_groups_exist()
    if request.user.is_authenticated:
        return redirect("sis:home")

    if request.method == "POST":
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data.get("first_name") or "",
                last_name=form.cleaned_data.get("last_name") or "",
                email=form.cleaned_data["email"],
                is_active=False,
            )
            profile = StudentProfile.objects.create(
                user=user,
                student_id=form.cleaned_data["student_id"],
                date_of_birth=form.cleaned_data.get("date_of_birth"),
                phone=form.cleaned_data.get("phone") or "",
                address=form.cleaned_data.get("address") or "",
                is_verified=False,
            )
            Group.objects.get_or_create(name=ROLE_STUDENT)[0].user_set.add(user)

            _notify_admins_for_student_verification(request, profile)
            messages.success(
                request,
                "Signup submitted. An administrator must approve your account before you can log in.",
            )
            return redirect("login")
    else:
        form = StudentSignupForm()
    return render(request, "sis/signup.html", {"form": form})


@require_any_group(ROLE_REGISTRY)
def signup_verify(request: HttpRequest, token: str) -> HttpResponse:
    """
    Admin/registry approves a student signup via signed token.
    """
    try:
        student_pk = _verification_signer().unsign(token, max_age=60 * 60 * 24 * 7)  # 7 days
    except SignatureExpired:
        messages.error(request, "Verification link expired.")
        return redirect("sis:home")
    except BadSignature:
        messages.error(request, "Invalid verification link.")
        return redirect("sis:home")

    student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=int(student_pk))

    if request.method == "POST":
        if not student.is_verified:
            student.is_verified = True
            student.verified_at = timezone.now()
            student.verified_by = request.user
            student.save(update_fields=["is_verified", "verified_at", "verified_by"])
        if not student.user.is_active:
            student.user.is_active = True
            student.user.save(update_fields=["is_active"])
        messages.success(request, f"Approved student {student.student_id}. They can now log in.")
        return redirect("sis:student_detail", pk=student.pk)

    return render(request, "sis/signup_verify.html", {"student": student})

# ----------------------------
# Student registration/profile
# ----------------------------


@require_any_group(ROLE_REGISTRY)
def student_list(request: HttpRequest) -> HttpResponse:
    students = StudentProfile.objects.select_related("user").order_by("student_id")
    q = (request.GET.get("q") or "").strip()
    if q:
        students = students.filter(
            models.Q(student_id__icontains=q)
            | models.Q(user__username__icontains=q)
            | models.Q(user__first_name__icontains=q)
            | models.Q(user__last_name__icontains=q)
            | models.Q(user__email__icontains=q)
        )
    return render(request, "sis/students/list.html", {"students": students, "q": q})


@require_any_group(ROLE_REGISTRY)
def student_export_csv(request: HttpRequest) -> HttpResponse:
    students = StudentProfile.objects.select_related("user").order_by("student_id")
    q = (request.GET.get("q") or "").strip()
    if q:
        students = students.filter(
            models.Q(student_id__icontains=q)
            | models.Q(user__username__icontains=q)
            | models.Q(user__first_name__icontains=q)
            | models.Q(user__last_name__icontains=q)
            | models.Q(user__email__icontains=q)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="students.csv"'
    w = csv.writer(response)
    w.writerow(["student_id", "username", "full_name", "email", "phone"])
    for s in students:
        w.writerow(
            [
                s.student_id,
                s.user.username,
                s.user.get_full_name(),
                s.user.email,
                s.phone,
            ]
        )
    return response


@require_any_group(ROLE_REGISTRY)
def student_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudentCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data.get("first_name") or "",
                last_name=form.cleaned_data.get("last_name") or "",
                email=form.cleaned_data.get("email") or "",
                is_active=True,
            )
            student = StudentProfile.objects.create(
                user=user,
                student_id=form.cleaned_data["student_id"],
                date_of_birth=form.cleaned_data.get("date_of_birth"),
                phone=form.cleaned_data.get("phone") or "",
                address=form.cleaned_data.get("address") or "",
                is_verified=True,
                verified_at=timezone.now(),
                verified_by=request.user,
            )
            Group.objects.get_or_create(name=ROLE_STUDENT)[0].user_set.add(user)
            messages.success(request, f"Student created: {student.student_id}")
            return redirect("sis:student_detail", pk=student.pk)
    else:
        form = StudentCreateForm()
    return render(request, "sis/students/create.html", {"form": form})


@require_any_group(ROLE_REGISTRY)
def student_detail(request: HttpRequest, pk: int) -> HttpResponse:
    student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
    invoices = student.invoices.all().order_by("-created_at")
    enrollments = student.enrollments.select_related("course").order_by("-created_at")
    results = Result.objects.filter(enrollment__student=student).select_related(
        "enrollment__course"
    )
    return render(
        request,
        "sis/students/detail.html",
        {"student": student, "invoices": invoices, "enrollments": enrollments, "results": results},
    )


@require_any_group(ROLE_REGISTRY)
def student_edit(request: HttpRequest, pk: int) -> HttpResponse:
    student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
    if request.method == "POST":
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            student.user.first_name = form.cleaned_data.get("first_name") or ""
            student.user.last_name = form.cleaned_data.get("last_name") or ""
            student.user.email = form.cleaned_data.get("email") or ""
            student.user.save(update_fields=["first_name", "last_name", "email"])
            messages.success(request, "Student updated.")
            return redirect("sis:student_detail", pk=student.pk)
    else:
        form = StudentEditForm(instance=student)
    return render(request, "sis/students/edit.html", {"student": student, "form": form})


@require_any_group(ROLE_STUDENT, ROLE_REGISTRY)
def my_profile(request: HttpRequest) -> HttpResponse:
    profile = getattr(request.user, "student_profile", None)
    if not profile:
        messages.info(request, "No student profile is linked to this account.")
        return redirect("sis:home")
    invoices = profile.invoices.all().order_by("-created_at")
    enrollments = profile.enrollments.select_related("course").order_by("-created_at")
    results = Result.objects.filter(enrollment__student=profile).select_related(
        "enrollment__course"
    )
    return render(
        request,
        "sis/students/me.html",
        {"student": profile, "invoices": invoices, "enrollments": enrollments, "results": results},
    )


@require_any_group(ROLE_STUDENT, ROLE_REGISTRY)
def my_profile_edit(request: HttpRequest) -> HttpResponse:
    profile = getattr(request.user, "student_profile", None)
    if not profile:
        messages.info(request, "No student profile is linked to this account.")
        return redirect("sis:home")

    # If registry staff hits this page, send them to the full edit screen.
    if user_in_group(request.user, ROLE_REGISTRY) and not user_in_group(request.user, ROLE_STUDENT):
        return redirect("sis:student_edit", pk=profile.pk)

    if request.method == "POST":
        form = StudentSelfEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("sis:my_profile")
    else:
        form = StudentSelfEditForm(instance=profile)
    return render(request, "sis/students/me_edit.html", {"student": profile, "form": form})


# ----------------------------
# Course registration/management
# ----------------------------


@require_any_group(ROLE_REGISTRY, ROLE_LECTURER, ROLE_STUDENT)
def course_list(request: HttpRequest) -> HttpResponse:
    qs = Course.objects.filter(is_active=True).select_related("lecturer").order_by("code")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(models.Q(code__icontains=q) | models.Q(title__icontains=q))
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        qs = qs.filter(lecturer=request.user)
    return render(request, "sis/courses/list.html", {"courses": qs, "q": q})


@require_any_group(ROLE_REGISTRY, ROLE_LECTURER)
def course_export_csv(request: HttpRequest) -> HttpResponse:
    qs = Course.objects.filter(is_active=True).select_related("lecturer").order_by("code")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(models.Q(code__icontains=q) | models.Q(title__icontains=q))
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        qs = qs.filter(lecturer=request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="courses.csv"'
    w = csv.writer(response)
    w.writerow(["code", "title", "credit_units", "lecturer", "is_active"])
    for c in qs:
        w.writerow([c.code, c.title, c.credit_units, getattr(c.lecturer, "username", ""), c.is_active])
    return response


@require_any_group(ROLE_REGISTRY)
def course_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Course created: {course.code}")
            return redirect("sis:course_detail", pk=course.pk)
    else:
        form = CourseForm()
    return render(request, "sis/courses/create.html", {"form": form})


@require_any_group(ROLE_REGISTRY, ROLE_LECTURER)
def course_detail(request: HttpRequest, pk: int) -> HttpResponse:
    course = get_object_or_404(Course.objects.select_related("lecturer"), pk=pk)
    enrollments = course.enrollments.select_related("student__user").order_by("-created_at")
    return render(request, "sis/courses/detail.html", {"course": course, "enrollments": enrollments})


@require_any_group(ROLE_REGISTRY)
def course_edit(request: HttpRequest, pk: int) -> HttpResponse:
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(request, "Course updated.")
            return redirect("sis:course_detail", pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(request, "sis/courses/edit.html", {"course": course, "form": form})


# ----------------------------
# Enrollment
# ----------------------------


@require_any_group(ROLE_REGISTRY, ROLE_STUDENT)
def enrollment_list(request: HttpRequest) -> HttpResponse:
    qs = Enrollment.objects.select_related("student__user", "course").order_by("-created_at")
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    if year.isdigit():
        qs = qs.filter(year=int(year))
    if semester.isdigit():
        qs = qs.filter(semester=int(semester))
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            models.Q(student__student_id__icontains=q)
            | models.Q(course__code__icontains=q)
            | models.Q(course__title__icontains=q)
        )
    if user_in_group(request.user, ROLE_STUDENT) and not request.user.is_superuser:
        profile = getattr(request.user, "student_profile", None)
        qs = qs.filter(student=profile) if profile else qs.none()
    return render(
        request,
        "sis/enrollments/list.html",
        {
            "enrollments": qs,
            "q": q,
            "year": year,
            "semester": semester,
            "status": status,
        },
    )


@require_any_group(ROLE_REGISTRY)
def enrollment_export_csv(request: HttpRequest) -> HttpResponse:
    qs = Enrollment.objects.select_related("student__user", "course").order_by("-created_at")
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    if year.isdigit():
        qs = qs.filter(year=int(year))
    if semester.isdigit():
        qs = qs.filter(semester=int(semester))
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            models.Q(student__student_id__icontains=q)
            | models.Q(course__code__icontains=q)
            | models.Q(course__title__icontains=q)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="enrollments.csv"'
    w = csv.writer(response)
    w.writerow(["student_id", "course_code", "course_title", "year", "semester", "status"])
    for e in qs:
        w.writerow([e.student.student_id, e.course.code, e.course.title, e.year, e.semester, e.status])
    return response


@require_any_group(ROLE_REGISTRY, ROLE_STUDENT)
def enrollment_create(request: HttpRequest) -> HttpResponse:
    profile = None
    is_student_self = user_in_group(request.user, ROLE_STUDENT) and not request.user.is_superuser
    if is_student_self:
        profile = getattr(request.user, "student_profile", None)

    if request.method == "POST":
        post = request.POST.copy()
        # Disabled fields don't submit; force the student's own profile for student self-enrollment.
        if is_student_self and profile:
            post["student"] = str(profile.pk)
        form = EnrollmentForm(post)
        if form.is_valid():
            form.save()
            messages.success(request, "Enrollment saved.")
            return redirect("sis:enrollment_list")
    else:
        form = EnrollmentForm()

    if is_student_self:
        if not profile:
            messages.info(request, "No student profile is linked to this account.")
            return redirect("sis:home")
        form.fields["student"].initial = profile
        form.fields["student"].disabled = True
    return render(request, "sis/enrollments/create.html", {"form": form})


@require_any_group(ROLE_REGISTRY)
def enrollment_edit(request: HttpRequest, pk: int) -> HttpResponse:
    enrollment = get_object_or_404(Enrollment.objects.select_related("student__user", "course"), pk=pk)
    if request.method == "POST":
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, "Enrollment updated.")
            return redirect("sis:enrollment_list")
    else:
        form = EnrollmentForm(instance=enrollment)
    return render(
        request,
        "sis/enrollments/edit.html",
        {"enrollment": enrollment, "form": form},
    )

# ----------------------------
# Fees / payments tracking
# ----------------------------


@require_any_group(ROLE_FINANCE, ROLE_STUDENT, ROLE_REGISTRY)
def fee_list(request: HttpRequest) -> HttpResponse:
    qs = FeeInvoice.objects.select_related("student__user").order_by("-created_at")
    status = (request.GET.get("status") or "").strip()
    year = (request.GET.get("year") or "").strip()
    q = (request.GET.get("q") or "").strip()
    if status:
        qs = qs.filter(status=status)
    if year.isdigit():
        qs = qs.filter(year=int(year))
    if q:
        qs = qs.filter(
            models.Q(student__student_id__icontains=q)
            | models.Q(student__user__username__icontains=q)
        )
    if user_in_group(request.user, ROLE_STUDENT) and not request.user.is_superuser:
        profile = getattr(request.user, "student_profile", None)
        qs = qs.filter(student=profile) if profile else qs.none()
    return render(
        request,
        "sis/fees/list.html",
        {"invoices": qs, "q": q, "status": status, "year": year},
    )


@require_any_group(ROLE_FINANCE, ROLE_REGISTRY)
def fee_export_csv(request: HttpRequest) -> HttpResponse:
    qs = FeeInvoice.objects.select_related("student__user").order_by("-created_at")
    status = (request.GET.get("status") or "").strip()
    year = (request.GET.get("year") or "").strip()
    q = (request.GET.get("q") or "").strip()
    if status:
        qs = qs.filter(status=status)
    if year.isdigit():
        qs = qs.filter(year=int(year))
    if q:
        qs = qs.filter(
            models.Q(student__student_id__icontains=q)
            | models.Q(student__user__username__icontains=q)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="fees.csv"'
    w = csv.writer(response)
    w.writerow(["invoice_id", "student_id", "year", "term", "amount_due", "amount_paid", "balance", "status"])
    for inv in qs:
        w.writerow([inv.id, inv.student.student_id, inv.year, inv.term, inv.amount_due, inv.amount_paid, inv.balance, inv.status])
    return response


@require_any_group(ROLE_FINANCE)
def fee_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = FeeInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save()
            messages.success(request, "Invoice created.")
            return redirect("sis:fee_list")
    else:
        form = FeeInvoiceForm()
    return render(request, "sis/fees/create.html", {"form": form})


@require_any_group(ROLE_FINANCE)
def payment_create(request: HttpRequest, pk: int) -> HttpResponse:
    invoice = get_object_or_404(FeeInvoice.objects.select_related("student__user"), pk=pk)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment: Payment = form.save(commit=False)
            payment.invoice = invoice
            payment.received_by = request.user
            payment.save()
            invoice.refresh_status()
            invoice.save(update_fields=["status"])
            messages.success(request, "Payment recorded.")
            return redirect("sis:fee_list")
    else:
        form = PaymentForm()
    return render(request, "sis/fees/pay.html", {"invoice": invoice, "form": form})


@require_any_group(ROLE_FINANCE)
def fee_edit(request: HttpRequest, pk: int) -> HttpResponse:
    invoice = get_object_or_404(FeeInvoice.objects.select_related("student__user"), pk=pk)
    if request.method == "POST":
        form = FeeInvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            invoice = form.save()
            invoice.refresh_status()
            invoice.save(update_fields=["status"])
            messages.success(request, "Invoice updated.")
            return redirect("sis:fee_list")
    else:
        form = FeeInvoiceForm(instance=invoice)
    return render(request, "sis/fees/edit.html", {"invoice": invoice, "form": form})

# ----------------------------
# Result management
# ----------------------------


@require_any_group(ROLE_LECTURER, ROLE_STUDENT, ROLE_REGISTRY)
def result_list(request: HttpRequest) -> HttpResponse:
    qs = Result.objects.select_related("enrollment__student__user", "enrollment__course").order_by(
        "-recorded_at"
    )
    q = (request.GET.get("q") or "").strip()
    course = (request.GET.get("course") or "").strip()
    if course:
        qs = qs.filter(enrollment__course__code__icontains=course)
    if q:
        qs = qs.filter(
            models.Q(enrollment__student__student_id__icontains=q)
            | models.Q(enrollment__course__code__icontains=q)
            | models.Q(enrollment__course__title__icontains=q)
        )
    if user_in_group(request.user, ROLE_STUDENT) and not request.user.is_superuser:
        profile = getattr(request.user, "student_profile", None)
        qs = qs.filter(enrollment__student=profile) if profile else qs.none()
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        qs = qs.filter(enrollment__course__lecturer=request.user)
    return render(
        request, "sis/results/list.html", {"results": qs, "q": q, "course": course}
    )


@require_any_group(ROLE_LECTURER, ROLE_REGISTRY)
def result_export_csv(request: HttpRequest) -> HttpResponse:
    qs = Result.objects.select_related("enrollment__student__user", "enrollment__course").order_by(
        "-recorded_at"
    )
    q = (request.GET.get("q") or "").strip()
    course = (request.GET.get("course") or "").strip()
    if course:
        qs = qs.filter(enrollment__course__code__icontains=course)
    if q:
        qs = qs.filter(
            models.Q(enrollment__student__student_id__icontains=q)
            | models.Q(enrollment__course__code__icontains=q)
            | models.Q(enrollment__course__title__icontains=q)
        )
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        qs = qs.filter(enrollment__course__lecturer=request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="results.csv"'
    w = csv.writer(response)
    w.writerow(["student_id", "course_code", "year", "semester", "ca_score", "exam_score", "total", "grade", "recorded_at"])
    for r in qs:
        e = r.enrollment
        w.writerow([e.student.student_id, e.course.code, e.year, e.semester, r.ca_score, r.exam_score, r.total, r.grade, r.recorded_at])
    return response


@require_any_group(ROLE_LECTURER, ROLE_REGISTRY)
def result_record(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ResultForm(request.POST)
        if form.is_valid():
            result: Result = form.save(commit=False)
            result.recorded_by = request.user
            result.save()
            messages.success(request, "Result recorded.")
            return redirect("sis:result_list")
    else:
        form = ResultForm()

        if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
            form.fields["enrollment"].queryset = Enrollment.objects.filter(
                course__lecturer=request.user
            ).select_related("student__user", "course")

    return render(request, "sis/results/record.html", {"form": form})


@require_any_group(ROLE_LECTURER, ROLE_REGISTRY)
def result_edit(request: HttpRequest, pk: int) -> HttpResponse:
    result = get_object_or_404(
        Result.objects.select_related("enrollment__student__user", "enrollment__course"), pk=pk
    )
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        if result.enrollment.course.lecturer_id != request.user.id:
            return redirect("sis:result_list")

    if request.method == "POST":
        form = ResultForm(request.POST, instance=result)
        if form.is_valid():
            result = form.save(commit=False)
            result.recorded_by = request.user
            result.save()
            messages.success(request, "Result updated.")
            return redirect("sis:result_list")
    else:
        form = ResultForm(instance=result)
        if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
            form.fields["enrollment"].queryset = Enrollment.objects.filter(
                course__lecturer=request.user
            ).select_related("student__user", "course")

    return render(request, "sis/results/edit.html", {"result": result, "form": form})

# ----------------------------
# Reports
# ----------------------------


@require_any_group(ROLE_REGISTRY, ROLE_FINANCE, ROLE_LECTURER)
def report_index(request: HttpRequest) -> HttpResponse:
    return render(request, "sis/reports/index.html")


@require_any_group(ROLE_FINANCE, ROLE_REGISTRY)
def report_fee_summary(request: HttpRequest) -> HttpResponse:
    qs = FeeInvoice.objects.select_related("student__user")
    total_due = qs.aggregate(s=Sum("amount_due"))["s"] or 0
    total_paid = sum((inv.amount_paid for inv in qs), 0)
    by_status = list(qs.values("status").annotate(c=Count("id")).order_by("status"))
    return render(
        request,
        "sis/reports/fee_summary.html",
        {"total_due": total_due, "total_paid": total_paid, "by_status": by_status},
    )


@require_any_group(ROLE_FINANCE, ROLE_REGISTRY)
def report_fee_summary_csv(request: HttpRequest) -> HttpResponse:
    qs = FeeInvoice.objects.select_related("student__user")
    total_due = qs.aggregate(s=Sum("amount_due"))["s"] or 0
    total_paid = sum((inv.amount_paid for inv in qs), 0)
    by_status = list(qs.values("status").annotate(c=Count("id")).order_by("status"))

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="report_fee_summary.csv"'
    w = csv.writer(response)
    w.writerow(["metric", "value"])
    w.writerow(["total_due", total_due])
    w.writerow(["total_paid", total_paid])
    w.writerow([])
    w.writerow(["status", "invoice_count"])
    for row in by_status:
        w.writerow([row["status"], row["c"]])
    return response


@require_any_group(ROLE_REGISTRY, ROLE_LECTURER)
def report_results_summary(request: HttpRequest) -> HttpResponse:
    qs = Result.objects.select_related("enrollment__course")
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        qs = qs.filter(enrollment__course__lecturer=request.user)

    by_course = (
        qs.values("enrollment__course__code", "enrollment__course__title")
        .annotate(
            avg_total=Avg(
                Cast(F("ca_score"), FloatField()) + Cast(F("exam_score"), FloatField())
            ),
            n=Count("id"),
        )
        .order_by("enrollment__course__code")
    )
    return render(request, "sis/reports/results_summary.html", {"by_course": list(by_course)})


@require_any_group(ROLE_REGISTRY, ROLE_LECTURER)
def report_results_summary_csv(request: HttpRequest) -> HttpResponse:
    qs = Result.objects.select_related("enrollment__course")
    if user_in_group(request.user, ROLE_LECTURER) and not request.user.is_superuser:
        qs = qs.filter(enrollment__course__lecturer=request.user)

    by_course = (
        qs.values("enrollment__course__code", "enrollment__course__title")
        .annotate(
            avg_total=Avg(
                Cast(F("ca_score"), FloatField()) + Cast(F("exam_score"), FloatField())
            ),
            n=Count("id"),
        )
        .order_by("enrollment__course__code")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="report_results_summary.csv"'
    w = csv.writer(response)
    w.writerow(["course_code", "course_title", "records", "avg_total"])
    for row in by_course:
        w.writerow(
            [
                row["enrollment__course__code"],
                row["enrollment__course__title"],
                row["n"],
                f'{row["avg_total"]:.2f}' if row["avg_total"] is not None else "",
            ]
        )
    return response
