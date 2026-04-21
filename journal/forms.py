from django import forms
from django.contrib.auth.models import User

from .models import (
    AdminProfile,
    Article,
    AuditLog,
    ContactMessage,
    EditorialBoardMember,
    Issue,
    Notification,
    PeerReviewComment,
    ReviewerAssignment,
    Submission,
    UserProfile,
    Volume,
)


class SearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    sort = forms.ChoiceField(
        required=False,
        choices=[("latest", "Latest"), ("oldest", "Oldest"), ("title", "Title")],
    )


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = [
            "volume",
            "full_name",
            "email",
            "affiliation",
            "title",
            "authors",
            "abstract",
            "keywords",
            "discipline",
            "manuscript",
        ]
        widgets = {"abstract": forms.Textarea(attrs={"rows": 5})}


class StatusTrackingForm(forms.Form):
    article_id = forms.CharField(max_length=20)


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "hcaptcha_token"]
        widgets = {"message": forms.Textarea(attrs={"rows": 5}), "hcaptcha_token": forms.HiddenInput()}


class AdminLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()


class VerifyOTPForm(forms.Form):
    email = forms.EmailField()
    otp_code = forms.CharField(max_length=6)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class VolumeForm(forms.ModelForm):
    class Meta:
        model = Volume
        fields = ["name", "issn", "editor_name", "publication_date", "thumbnail", "description", "is_active"]
        widgets = {
            "publication_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["volume", "title", "number", "publication_date", "summary", "is_active"]
        widgets = {
            "publication_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(attrs={"rows": 3}),
        }


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = [
            "volume",
            "issue",
            "category",
            "title",
            "authors",
            "abstract",
            "pdf_file",
            "pdf_url",
            "doi",
            "citation_text",
            "is_active",
        ]
        widgets = {
            "abstract": forms.Textarea(attrs={"rows": 5}),
            "citation_text": forms.Textarea(attrs={"rows": 3}),
        }


class EditorialBoardForm(forms.ModelForm):
    class Meta:
        model = EditorialBoardMember
        fields = ["name", "role", "bio", "email", "profile_picture", "order", "is_active"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}


class SubmissionReviewForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["status", "rejection_reason", "reviewer_notes", "plagiarism_score"]
        widgets = {
            "rejection_reason": forms.Textarea(attrs={"rows": 3}),
            "reviewer_notes": forms.Textarea(attrs={"rows": 4}),
        }


class AdminUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    can_manage_admins = forms.BooleanField(required=False)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=False)
    profile_picture = forms.ImageField(required=False, widget=forms.ClearableFileInput())

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "is_active", "is_staff"]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            AdminProfile.objects.update_or_create(
                user=user,
                defaults={"can_manage_admins": self.cleaned_data.get("can_manage_admins", False)},
            )
            profile, _ = UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": self.cleaned_data.get("role") or UserProfile.ROLE_EDITOR},
            )
            profile.profile_picture = self.cleaned_data.get("profile_picture")
            profile.save()
        return user


class UserEditForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, label="New Password (leave blank to keep current)")
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label="User Role")
    profile_picture = forms.ImageField(required=False, widget=forms.ClearableFileInput())

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "is_active", "is_staff"]
    
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if self.profile:
            self.fields['role'].initial = self.profile.role

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile, _ = UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": self.cleaned_data.get("role")}
            )
            profile.profile_picture = self.cleaned_data.get("profile_picture")
            profile.save()
            if user.is_staff:
                AdminProfile.objects.update_or_create(user=user)
        return user



class PeerReviewCommentForm(forms.ModelForm):
    class Meta:
        model = PeerReviewComment
        fields = ["comment", "is_visible_to_author"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}


class AuthorRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    affiliation = forms.CharField(required=False)
    orcid = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": UserProfile.ROLE_AUTHOR,
                    "affiliation": self.cleaned_data.get("affiliation", ""),
                    "orcid": self.cleaned_data.get("orcid", ""),
                },
            )
        return user


class ReviewerAssignmentForm(forms.ModelForm):
    class Meta:
        model = ReviewerAssignment
        fields = ["reviewer", "due_date", "status"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}


class ReviewerResponseForm(forms.ModelForm):
    class Meta:
        model = ReviewerAssignment
        fields = ["status", "recommendation", "review_summary"]
        widgets = {"review_summary": forms.Textarea(attrs={"rows": 4})}


class UnifiedAuthForm(forms.Form):
    action = forms.ChoiceField(
        choices=[("login", "Login"), ("register", "Register")],
        widget=forms.HiddenInput()
    )
    # Login fields
    username = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    # Register fields
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    reg_username = forms.CharField(max_length=150, required=False)
    reg_password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=False,
        label="Role (for new accounts)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        if action == "login":
            if not cleaned_data.get("username") or not cleaned_data.get("password"):
                raise forms.ValidationError("Username and password are required for login.")
        elif action == "register":
            if not all([cleaned_data.get(k) for k in ["reg_username", "reg_password", "email"]]):
                raise forms.ValidationError("Username, email, and password required for registration.")
            if cleaned_data.get("reg_password") != cleaned_data.get("confirm_password"):
                raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    profile_picture = forms.ImageField(required=False, widget=forms.ClearableFileInput())

    class Meta:
        model = UserProfile
        fields = ["affiliation", "orcid", "bio"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["email"].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data.get("first_name", "")
        self.user.last_name = self.cleaned_data.get("last_name", "")
        self.user.email = self.cleaned_data.get("email", "")
        profile.profile_picture = self.cleaned_data.get("profile_picture")
        if commit:
            self.user.save()
            profile.save()
        return profile
