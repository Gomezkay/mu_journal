from django.urls import path, reverse_lazy
from django.shortcuts import redirect

from . import views
from .feeds import LatestArticlesFeed

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about_page, name="about"),
    path("guidelines/", views.guidelines_page, name="guidelines"),
    path("editorial-board/", views.editorial_board_page, name="editorial-board"),
    path("contact/", views.contact_page, name="contact"),
    path("submit/", views.submit_paper, name="submit-paper"),
    path("submissions/<int:pk>/edit/", views.submission_edit, name="submission-edit"),
    path("track/", views.track_submission, name="track-submission"),
    path("sign-in/", views.unified_sign_in, name="unified-sign-in"),
    path("verify-pending/", views.verify_pending, name="verify-pending"),
    path("verify-email/<str:token>/", views.verify_email, name="verify-email"),
    # Deprecated
    # Legacy - redirect or remove later
    path("account/login/", lambda r: redirect("unified-sign-in"), name="account-login"),
    path("account/register/", lambda r: redirect("unified-sign-in"), name="account-register"),
    path("account/logout/", views.account_logout, name="account-logout"),

    path("dashboard/", views.author_dashboard, name="author-dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("reviewer/dashboard/", views.reviewer_dashboard, name="reviewer-dashboard"),
    path("reviewer/assignments/<int:pk>/", views.reviewer_assignment_detail, name="reviewer-assignment-detail"),
    path("volumes/<slug:slug>/", views.volume_detail, name="volume-detail"),
    path("articles/<slug:slug>/", views.article_detail, name="article-detail"),
    path("rss/", LatestArticlesFeed(), name="rss-feed"),
    path("admin/login/", views.admin_login_view, name="admin-login"),
    path("admin/logout/", views.admin_logout_view, name="admin-logout"),
    path("admin/register/", views.admin_register_view, name="admin-register"),
    path("admin/forgot-password/", views.admin_forgot_password, name="admin-forgot-password"),
    path("admin/reset-password/", views.admin_reset_password, name="admin-reset-password"),
    path("admin/dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("admin/volumes/", views.volume_list, name="volume-list"),
    path("admin/volumes/add/", views.volume_create, name="volume-create"),
    path("admin/volumes/<int:pk>/edit/", views.volume_update, name="volume-update"),
    path("admin/volumes/<int:pk>/toggle/", views.volume_toggle, name="volume-toggle"),
    path("admin/issues/add/", views.issue_create, name="issue-create"),
    path("admin/articles/", views.article_list, name="article-list"),
    path("admin/articles/add/", views.article_create, name="article-create"),
    path("admin/articles/<int:pk>/edit/", views.article_update, name="article-update"),
    path("admin/articles/<int:pk>/toggle/", views.article_toggle, name="article-toggle"),
    path("admin/submissions/", views.submission_list, name="submission-list"),
    path("admin/submissions/export/csv/", views.export_submissions_csv_view, name="export-submissions-csv"),
    path("admin/submissions/export/excel/", views.export_submissions_excel_view, name="export-submissions-excel"),
    path("admin/submissions/<int:pk>/review/", views.submission_review, name="submission-review"),
    path("admin/users/", views.admin_user_list_all, name="admin-user-list"),
    path("admin/users/add/", views.admin_user_edit, name="admin-user-add"),
    path("admin/users/<int:pk>/edit/", views.admin_user_edit, name="admin-user-edit"),

    path("admin/users/<int:pk>/delete/", views.admin_user_delete, name="admin-user-delete"),

    path("admin/board/", views.editorial_board_list, name="admin-editorial-board-list"),
    path("admin/board/add/", views.editorial_board_create, name="admin-editorial-board-add"),
    path("admin/board/<int:pk>/edit/", views.editorial_board_edit, name="admin-editorial-board-edit"),
    path("admin/board/<int:pk>/delete/", views.editorial_board_delete, name="admin-editorial-board-delete"),
]
