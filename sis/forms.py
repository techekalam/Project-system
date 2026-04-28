from __future__ import annotations

from django import forms
from django.contrib.auth.models import User

from .models import Course, Enrollment, FeeInvoice, Payment, Result, StudentProfile


class StudentCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    student_id = forms.CharField(max_length=32)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    phone = forms.CharField(max_length=32, required=False)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"]
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("Student ID already exists.")
        return student_id


class StudentSignupForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()

    student_id = forms.CharField(max_length=32)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    phone = forms.CharField(max_length=32, required=False)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"]
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("Student ID already exists.")
        return student_id


class StudentEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = StudentProfile
        fields = ["student_id", "date_of_birth", "phone", "address"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"]
        qs = StudentProfile.objects.filter(student_id=student_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Student ID already exists.")
        return student_id


class StudentSelfEditForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["date_of_birth", "phone", "address"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "title", "credit_units", "lecturer", "is_active"]


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["student", "course", "year", "semester", "status"]


class FeeInvoiceForm(forms.ModelForm):
    class Meta:
        model = FeeInvoice
        fields = ["student", "year", "term", "amount_due", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "reference"]


class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ["enrollment", "ca_score", "exam_score"]

