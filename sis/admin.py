from django.contrib import admin

from .models import Course, Enrollment, FeeInvoice, Payment, Result, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("student_id", "user", "phone", "created_at")
    search_fields = ("student_id", "user__username", "user__first_name", "user__last_name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "credit_units", "lecturer", "is_active")
    search_fields = ("code", "title")
    list_filter = ("is_active",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "year", "semester", "status", "created_at")
    list_filter = ("year", "semester", "status")
    search_fields = ("student__student_id", "course__code", "course__title")


@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "year", "term", "amount_due", "status", "created_at")
    list_filter = ("status", "year", "term")
    search_fields = ("student__student_id", "student__user__username")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "amount", "paid_at", "received_by", "reference")
    list_filter = ("paid_at",)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "ca_score", "exam_score", "total", "grade", "recorded_at")
    list_filter = ("recorded_at",)
