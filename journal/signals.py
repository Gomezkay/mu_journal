from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AdminProfile, AdminSessionLog, UserProfile


@receiver(post_save, sender="auth.User")
def ensure_admin_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
    if instance.is_staff:
        AdminProfile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    if user.is_staff:
        AdminSessionLog.objects.create(user=user, ip_address=request.META.get("REMOTE_ADDR"))


@receiver(user_logged_out)
def log_admin_logout(sender, request, user, **kwargs):
    if user and user.is_staff:
        session = AdminSessionLog.objects.filter(user=user, is_active=True).first()
        if session:
            session.is_active = False
            session.logout_time = session.updated_at
            session.save(update_fields=["is_active", "logout_time", "updated_at"])
