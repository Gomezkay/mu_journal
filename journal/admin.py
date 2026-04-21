from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AdminProfile,
    AdminSessionLog,
    Article,
    AuditLog,
    ContactMessage,
    EditorialBoardMember,
    Issue,
    Notification,
    PasswordResetOTP,
    PeerReviewComment,
    ReviewerAssignment,
    Submission,
    UserProfile,
    Volume,
)


class EditorialBoardMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'email', 'profile_picture_thumbnail']
    list_filter = ['is_active']
    search_fields = ['name', 'role', 'email']
    ordering = ['order', 'name']

    def profile_picture_thumbnail(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 50%;" />',
                obj.profile_picture.url
            )
        return format_html('<span class="text-muted">No image</span>')
    profile_picture_thumbnail.short_description = 'Profile Picture'

    fieldsets = (
        ('Member Information', {
            'fields': ('name', 'role', 'bio', 'email', 'profile_picture'),
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active'),
        }),
    )


admin.site.register(
    [
        Volume,
        Issue,
        Article,
        Submission,
        EditorialBoardMember,
        ContactMessage,
        AdminProfile,
        AdminSessionLog,
        UserProfile,
        ReviewerAssignment,
        Notification,
        AuditLog,
        PasswordResetOTP,
        PeerReviewComment,
    ]
)
admin.site.unregister(EditorialBoardMember)
admin.site.register(EditorialBoardMember, EditorialBoardMemberAdmin)
