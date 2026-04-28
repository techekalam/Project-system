from django.urls import path

from . import views


app_name = "sis"

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("signup/verify/<str:token>/", views.signup_verify, name="signup_verify"),
    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/export.csv", views.student_export_csv, name="student_export_csv"),
    path("students/new/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("me/profile/", views.my_profile, name="my_profile"),
    path("me/profile/edit/", views.my_profile_edit, name="my_profile_edit"),
    # Courses
    path("courses/", views.course_list, name="course_list"),
    path("courses/export.csv", views.course_export_csv, name="course_export_csv"),
    path("courses/new/", views.course_create, name="course_create"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    # Enrollment
    path("enrollments/", views.enrollment_list, name="enrollment_list"),
    path("enrollments/export.csv", views.enrollment_export_csv, name="enrollment_export_csv"),
    path("enrollments/new/", views.enrollment_create, name="enrollment_create"),
    path("enrollments/<int:pk>/edit/", views.enrollment_edit, name="enrollment_edit"),
    # Fees/Payments
    path("fees/", views.fee_list, name="fee_list"),
    path("fees/export.csv", views.fee_export_csv, name="fee_export_csv"),
    path("fees/new/", views.fee_create, name="fee_create"),
    path("fees/<int:pk>/edit/", views.fee_edit, name="fee_edit"),
    path("fees/<int:pk>/pay/", views.payment_create, name="payment_create"),
    # Results
    path("results/", views.result_list, name="result_list"),
    path("results/export.csv", views.result_export_csv, name="result_export_csv"),
    path("results/record/", views.result_record, name="result_record"),
    path("results/<int:pk>/edit/", views.result_edit, name="result_edit"),
    # Reports
    path("reports/", views.report_index, name="report_index"),
    path("reports/fee-summary/", views.report_fee_summary, name="report_fee_summary"),
    path("reports/fee-summary.csv", views.report_fee_summary_csv, name="report_fee_summary_csv"),
    path("reports/results-summary/", views.report_results_summary, name="report_results_summary"),
    path("reports/results-summary.csv", views.report_results_summary_csv, name="report_results_summary_csv"),
]

