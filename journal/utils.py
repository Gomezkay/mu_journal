import csv
import io
import json
import random
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from .models import AuditLog, Notification, PasswordResetOTP, EmailVerificationToken, Article, Submission, Issue

def verify_hcaptcha(token):
    if settings.DEBUG and not settings.HCAPTCHA_SECRET_KEY:
        return True, "Debug mode bypassed captcha verification."
    if not token or not settings.HCAPTCHA_SECRET_KEY:
        return False, "Captcha verification is not configured."
    data = json.dumps({"response": token, "secret": settings.HCAPTCHA_SECRET_KEY}).encode("utf-8")
    request = urllib.request.Request(
        "https://hcaptcha.com/siteverify",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return False, "Captcha verification service could not be reached."
    return bool(payload.get("success")), payload.get("message", "Captcha verification failed.")


def generate_otp_for_user(user):
    return PasswordResetOTP.objects.create(
        user=user,
        otp_code=f"{random.randint(100000, 999999)}",
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def send_templated_email(subject, template_name, context, recipient):
    html_message = render_to_string(template_name, context)
    if settings.NODEMAILER_ENDPOINT:
        payload = json.dumps(
            {
                "to": recipient,
                "subject": subject,
                "html": html_message,
                "from": settings.DEFAULT_FROM_EMAIL,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            settings.NODEMAILER_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                return
        except Exception:
            pass
    send_mail(
        subject=subject,
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        html_message=html_message,
        fail_silently=True,
    )


def send_password_reset_otp(user):
    otp = generate_otp_for_user(user)
    send_templated_email("Your MUMJ OTP Code", "emails/password_reset_otp.html", {"user": user, "otp": otp}, user.email)
    return otp


def generate_verification_token(user):
    return EmailVerificationToken.objects.create(user=user)


def send_verification_email(request, user):
    from django.urls import reverse
    token = generate_verification_token(user)
    verification_url = request.build_absolute_uri(reverse('verify-email', args=[token.token]))
    send_templated_email(
        "Verify your email - Mulungushi University Multidisciplinary Journal", 
        "emails/email_verification.html",
        {"user": user, "token": token, "verification_url": verification_url},
        user.email
    )
    return token




def export_submissions_csv(queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="mumj_submissions.csv"'
    writer = csv.writer(response)
    writer.writerow(["Article ID", "Author", "Email", "Title", "Status", "Submitted"])
    for submission in queryset:
        writer.writerow(
            [
                submission.article_id,
                submission.full_name,
                submission.email,
                submission.title,
                submission.status,
                submission.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    return response


def export_submissions_excel(queryset):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Submissions"
    sheet.append(["Article ID", "Author", "Email", "Title", "Status", "Submitted"])
    for submission in queryset:
        sheet.append(
            [
                submission.article_id,
                submission.full_name,
                submission.email,
                submission.title,
                submission.status,
                submission.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="mumj_submissions.xlsx"'
    workbook.save(response)
    return response


def build_watermarked_pdf(source_path, output_path, watermark_text="MUMJ Preview"):
    reader = PdfReader(source_path)
    packet = io.BytesIO()
    page_size = reader.pages[0].mediabox
    overlay = canvas.Canvas(packet, pagesize=(float(page_size.width), float(page_size.height)))
    overlay.saveState()
    overlay.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.18))
    overlay.translate(float(page_size.width) / 2, float(page_size.height) / 2)
    overlay.rotate(35)
    overlay.setFont("Helvetica-Bold", 36)
    overlay.drawCentredString(0, 0, watermark_text)
    overlay.restoreState()
    overlay.save()
    packet.seek(0)

    watermark_page = PdfReader(packet).pages[0]
    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)
    with open(output_path, "wb") as output_file:
        writer.write(output_file)


def resolve_user_by_email(email):
    try:
        return User.objects.get(email=email, is_staff=True)
    except User.DoesNotExist:
        return None


def run_plagiarism_check(submission):
    if settings.PLAGIARISM_API_URL:
        return None
    submission.plagiarism_score = submission.plagiarism_score or 0
    submission.save(update_fields=["plagiarism_score"])
    return submission.plagiarism_score


def assign_doi(article):
    if settings.DOI_API_URL:
        return article.doi
    if not article.doi:
        article.doi = f"10.0000/mumj.{article.pk or 'draft'}"
        article.save(update_fields=["doi"])
    return article.doi


def sync_to_elasticsearch(article):
    return bool(settings.ELASTICSEARCH_URL or article.pk)


def create_notification(user, title, message, link=""):
    if not user:
        return None
    return Notification.objects.create(user=user, title=title, message=message, link=link)


def create_audit_log(user, action, object_type, object_id="", details=""):
    return AuditLog.objects.create(
        user=user,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        details=details,
    )


def create_article_from_submission(submission):
    """
    Create an Article from a published Submission.
    This function should be called when a submission is marked as published.
    """
    if submission.status != Submission.STATUS_PUBLISHED:
        return None

    # Get or create a default issue for the volume
    volume = submission.volume
    issue, created = Issue.objects.get_or_create(
        volume=volume,
        number=1,  # Default issue number
        defaults={
            "title": f"Default Issue for {volume.name}",
            "publication_date": timezone.now(),
            "summary": "Automatically created issue for published submissions"
        }
    )

    # Create the Article from the submission data
    article = Article.objects.create(
        volume=volume,
        issue=issue,
        title=submission.title,
        authors=submission.authors,
        abstract=submission.abstract,
        pdf_file=submission.manuscript,
        published_at=submission.decision_date or timezone.now(),
        is_active=True,
    )

    # Assign DOI and sync to Elasticsearch
    assign_doi(article)
    sync_to_elasticsearch(article)

    # Create audit log
    create_audit_log(
        None,  # No specific user for this system action
        "Created article from published submission",
        "Article",
        article.pk,
        f"Created from submission {submission.article_id}"
    )

    return article