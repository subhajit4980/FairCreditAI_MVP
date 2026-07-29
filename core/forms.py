from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import BankStatement, CustomerProfile, Document, User


class CustomerSignupForm(UserCreationForm):
    full_name = forms.CharField(max_length=120)
    mobile = forms.CharField(max_length=15)
    pan = forms.CharField(max_length=10, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "full_name", "mobile", "pan", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        user.mobile = self.cleaned_data["mobile"]
        user.pan = (self.cleaned_data.get("pan") or "").upper()
        user.email = self.cleaned_data.get("email") or ""
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user, full_name=self.cleaned_data["full_name"])
        return user


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = (
            "full_name",
            "date_of_birth",
            "gender",
            "education",
            "address",
            "occupation",
            "aadhaar_last4",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("doc_type", "file")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10MB).")
        name = f.name.lower()
        if not name.endswith((".pdf", ".jpg", ".jpeg", ".png")):
            raise forms.ValidationError("Only PDF, JPG, or PNG files allowed.")
        return f


class BankStatementUploadForm(forms.ModelForm):
    class Meta:
        model = BankStatement
        fields = ("file",)

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10MB).")
        if not f.name.lower().endswith((".csv", ".xls", ".xlsx")):
            raise forms.ValidationError("CSV, XLS, or XLSX only.")
        return f


class StaffUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep existing password.")

    class Meta:
        model = User
        fields = ("username", "email", "role", "is_active", "mobile")

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get("password")
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user
