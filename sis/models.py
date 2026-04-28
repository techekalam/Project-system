from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=32, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_students",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self) -> str:
        return f"{self.student_id} - {self.user.get_full_name() or self.user.username}"


class Course(models.Model):
    code = models.CharField(max_length=16, unique=True)
    title = models.CharField(max_length=200)
    credit_units = models.PositiveSmallIntegerField(default=3)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses_taught",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ENROLLED = "ENROLLED", "Enrolled"
        DROPPED = "DROPPED", "Dropped"

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    year = models.PositiveSmallIntegerField()
    semester = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ENROLLED)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course", "year", "semester"], name="uniq_enrollment_term"
            )
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.course.code} ({self.year}/{self.semester})"


class FeeInvoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIAL = "PARTIAL", "Partial"
        PAID = "PAID", "Paid"

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="invoices")
    year = models.PositiveSmallIntegerField()
    term = models.CharField(max_length=32, default="Tuition")
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNPAID)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self) -> str:
        return f"Invoice #{self.id} {self.student.student_id} {self.year} ({self.status})"

    @property
    def amount_paid(self):
        total = self.payments.aggregate(s=models.Sum("amount")).get("s") or 0
        return total

    @property
    def balance(self):
        return self.amount_due - self.amount_paid

    def refresh_status(self):
        if self.amount_paid <= 0:
            self.status = self.Status.UNPAID
        elif self.balance <= 0:
            self.status = self.Status.PAID
        else:
            self.status = self.Status.PARTIAL


class Payment(models.Model):
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=64, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self) -> str:
        return f"Payment #{self.id} Invoice #{self.invoice_id} {self.amount}"


class Result(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="result")
    ca_score = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(40)]
    )
    exam_score = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(60)]
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    recorded_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [models.Index(fields=["recorded_at"])]

    def __str__(self) -> str:
        return f"Result {self.enrollment.student.student_id} - {self.enrollment.course.code}"

    @property
    def total(self):
        return self.ca_score + self.exam_score

    @property
    def grade(self):
        t = float(self.total)
        if t >= 70:
            return "A"
        if t >= 60:
            return "B"
        if t >= 50:
            return "C"
        if t >= 45:
            return "D"
        if t >= 40:
            return "E"
        return "F"
