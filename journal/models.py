import uuid

from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Volume(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    issn = models.CharField(max_length=50)
    editor_name = models.CharField(max_length=255)
    publication_date = models.DateField()
    thumbnail = models.ImageField(upload_to="volumes/thumbnails/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-publication_date", "-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            candidate = base
            counter = 1
            while Volume.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                counter += 1
                candidate = f"{base}-{counter}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("volume-detail", args=[self.slug])


class Issue(TimeStampedModel):
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=255)
    number = models.PositiveIntegerField()
    publication_date = models.DateField()
    summary = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("volume", "number")
        ordering = ["-publication_date", "number"]

    def __str__(self):
        return f"{self.volume.name} - Issue {self.number}"


class Article(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("research", "Research Article"),
        ("review", "Review Paper"),
        ("case-study", "Case Study"),
        ("editorial", "Editorial"),
        ("short-communication", "Short Communication"),
    ]

    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, related_name="articles")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="articles")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    authors = models.CharField(max_length=500)
    abstract = models.TextField(blank=True)
    pdf_file = models.FileField(
        upload_to="articles/pdfs/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf"])],
    )
    pdf_url = models.URLField(blank=True)
    doi = models.CharField(max_length=120, blank=True)
    citation_text = models.TextField(blank=True)
    preview_watermark_ready = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    published_at = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            candidate = base
            counter = 1
            while Article.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                counter += 1
                candidate = f"{base}-{counter}"
            self.slug = candidate
        if not self.citation_text:
            self.citation_text = self.default_citation()
        super().save(*args, **kwargs)

    @property
    def pdf_link(self):
        if self.pdf_file:
            return self.pdf_file.url
        return self.pdf_url

    def default_citation(self):
        year = self.published_at.year if self.published_at else timezone.now().year
        return f"{self.authors} ({year}). {self.title}. {self.volume.name}, Issue {self.issue.number}."


class Submission(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_SCREENING = "screening"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_REVISION_REQUESTED = "revision_requested"
    STATUS_ACCEPTED = "accepted"
    STATUS_SCHEDULED = "scheduled"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_SCREENING, "Editor Screening"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_REVISION_REQUESTED, "Revision Requested"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_REJECTED, "Rejected"),
    ]

    article_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="submissions")
    volume = models.ForeignKey(Volume, on_delete=models.SET_NULL, null=True, blank=True, related_name="submissions")
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    affiliation = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=500)
    abstract = models.TextField()
    manuscript = models.FileField(upload_to="submissions/", validators=[FileExtensionValidator(["pdf"])])
    keywords = models.CharField(max_length=255, blank=True)
    discipline = models.CharField(max_length=120, blank=True)
    plagiarism_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    rejection_reason = models.TextField(blank=True)
    reviewer_notes = models.TextField(blank=True)
    decision_letter = models.TextField(blank=True)
    assigned_editor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editorial_submissions",
    )
    decision_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.article_id} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.article_id:
            self.article_id = f"MUMJ-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class EditorialBoardMember(TimeStampedModel):
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    profile_picture = models.ImageField(upload_to="board/", blank=True, null=True, help_text="Profile picture for board member")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    hcaptcha_token = models.CharField(max_length=500, blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.subject}"


class AdminProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    display_name = models.CharField(max_length=255, blank=True)
    can_manage_admins = models.BooleanField(default=False)

    def __str__(self):
        return self.display_name or self.user.get_full_name() or self.user.username


class UserProfile(TimeStampedModel):
    ROLE_AUTHOR = "author"
    ROLE_REVIEWER = "reviewer"
    ROLE_EDITOR = "editor"
    ROLE_MANAGING_EDITOR = "managing_editor"
    ROLE_CHOICES = [
        (ROLE_AUTHOR, "Author"),
        (ROLE_REVIEWER, "Reviewer"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_MANAGING_EDITOR, "Managing Editor"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_AUTHOR)
    affiliation = models.CharField(max_length=255, blank=True)
    orcid = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True, help_text="User profile picture")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class AdminSessionLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="admin_sessions")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-login_time"]

    def __str__(self):
        return f"{self.user.username} @ {self.login_time:%Y-%m-%d %H:%M}"



class PasswordResetOTP(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_otps")
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at


class EmailVerificationToken(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_tokens")
    token = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at


class PeerReviewComment(TimeStampedModel):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="comments")
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    is_visible_to_author = models.BooleanField(default=False)



class ReviewerAssignment(TimeStampedModel):
    STATUS_INVITED = "invited"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_INVITED, "Invited"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_COMPLETED, "Completed"),
    ]

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="review_assignments")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="review_assignments")
    due_date = models.DateField(blank=True, null=True)
    recommendation = models.CharField(max_length=120, blank=True)
    review_summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INVITED)

    class Meta:
        unique_together = ("submission", "reviewer")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.submission.article_id} -> {self.reviewer.username}"


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=255)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.object_type}"
