from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AdminLoginForm,
    AdminUserForm,
    AuthorRegistrationForm,
    ArticleForm,
    ContactForm,
    EditorialBoardForm,
    ForgotPasswordForm,
    IssueForm,
    PeerReviewCommentForm,
    ProfileForm,
    UnifiedAuthForm,
    UserEditForm,
    ReviewerAssignmentForm,
    ReviewerResponseForm,
    SearchForm,
    StatusTrackingForm,
    SubmissionForm,
    SubmissionReviewForm,
    VerifyOTPForm,
    VolumeForm,
)

from .models import (
    AdminProfile,
    AdminSessionLog,
    Article,
    AuditLog,
    EditorialBoardMember,
    EmailVerificationToken,
    Notification,
    ReviewerAssignment,
    Submission,
    UserProfile,
    Volume,
)
from .utils import (
    assign_doi,
    create_audit_log,
    create_notification,
    export_submissions_csv,
    export_submissions_excel,
    resolve_user_by_email,
    run_plagiarism_check,
    send_password_reset_otp,
    send_verification_email,
    sync_to_elasticsearch,
    verify_hcaptcha,
)


def get_role_redirect(user):
    """Determine redirect URL based on user role or staff status."""
    if not user.is_active:
        return "verify-pending"
    if user.is_staff:
        return "admin-dashboard"
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.role in [UserProfile.ROLE_REVIEWER, UserProfile.ROLE_EDITOR, UserProfile.ROLE_MANAGING_EDITOR]:
        return "reviewer-dashboard"
    return "author-dashboard"



def unified_sign_in(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect(request.user))
    
    form = UnifiedAuthForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        action = form.cleaned_data["action"]
        
        if action == "login":
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    redirect_url = get_role_redirect(user)
                    messages.success(request, "Welcome back!")
                    return redirect(redirect_url)
                messages.error(request, "Account is deactivated. Please verify your email.")
            else:
                messages.error(request, "Invalid username or password.")
        
        elif action == "register":
            username = form.cleaned_data["reg_username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["reg_password"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            role = form.cleaned_data["role"]
            
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken.")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False
                )
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={"role": role}
                )
                send_verification_email(request, user)
                create_audit_log(None, "Registered new account (pending verification)", "User", user.pk, f"{role} via {email}")
                messages.success(request, f"Account created for {email}. Check your email to verify and activate.")
                return redirect("verify-pending")
    
    return render(request, "public/unified_sign_in.html", {"form": form})


def verify_pending(request):
    if request.user.is_authenticated:
        if request.user.is_active:
            return redirect(get_role_redirect(request.user))
        user = request.user
    else:
        username = request.GET.get('username') or request.session.get('pending_username')
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = None
        else:
            user = None
    
    if request.method == "POST":
        if user and not user.is_active:
            send_verification_email(request, user)
            request.session['pending_username'] = user.username
            messages.success(request, "Verification email resent. Check your inbox.")
        return redirect("verify-pending")
    
    return render(request, "public/verify_pending.html", {"user": user})


def verify_email(request, token):
    from django.utils import timezone
    try:
        token_obj = EmailVerificationToken.objects.get(token=token)
        if token_obj.is_used or timezone.now() > token_obj.expires_at:
            messages.error(request, "Verification link expired or already used.")
            return redirect("unified-sign-in")
        
        user = token_obj.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])
        
        login(request, user)
        create_audit_log(user, "Email verified", "User", user.pk, "Account activated")
        messages.success(request, "Email verified! Welcome to your dashboard.")
        return redirect(get_role_redirect(user))
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, "Invalid verification link.")
        return redirect("unified-sign-in")







def staff_required(view):
    return login_required(user_passes_test(lambda u: u.is_staff and u.is_active, login_url="admin-login")(view))


def super_admin_required(view):
    check = lambda u: u.is_superuser or getattr(getattr(u, "admin_profile", None), "can_manage_admins", False)
    return staff_required(user_passes_test(check)(view))


def role_required(*roles):
    def decorator(view):
        return login_required(
            user_passes_test(
                lambda u: hasattr(u, "profile") and u.profile.role in roles,
                login_url="account-login",
            )(view)
        )

    return decorator


def home(request):
    form = SearchForm(request.GET or None)
    volumes = Volume.objects.filter(is_active=True).prefetch_related("issues", "articles")
    articles = Article.objects.filter(is_active=True).select_related("volume", "issue").order_by('-published_at')
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "latest")
    year = request.GET.get("year", "").strip()

    if query:
        volumes = volumes.filter(
            Q(name__icontains=query) | Q(editor_name__icontains=query) | Q(articles__title__icontains=query)
        ).distinct()
        articles = articles.filter(Q(title__icontains=query) | Q(authors__icontains=query))
    if year:
        volumes = volumes.filter(publication_date__year=year)
    if sort == "oldest":
        volumes = volumes.order_by("publication_date")
        articles = articles.order_by("published_at")
    elif sort == "title":
        volumes = volumes.order_by("name")
        articles = articles.order_by("title")

    context = {
        "form": form,
        "volumes": volumes,
        "latest_articles": articles[:8],
        "years": Volume.objects.dates("publication_date", "year", order="DESC"),
        "editorial_members": EditorialBoardMember.objects.filter(is_active=True)[:6],
    }
    return render(request, "public/home.html", context)


def article_detail(request, slug):
    article = get_object_or_404(Article.objects.select_related("volume", "issue"), slug=slug, is_active=True)
    return render(request, "public/article_detail.html", {"article": article})


def volume_detail(request, slug):
    volume = get_object_or_404(Volume.objects.prefetch_related("issues__articles"), slug=slug, is_active=True)
    return render(request, "public/volume_detail.html", {"volume": volume})


def about_page(request):
    return render(request, "public/page.html", {"title": "About MUMJ", "page_key": "about"})


def guidelines_page(request):
    return render(request, "public/page.html", {"title": "Author Guidelines", "page_key": "guidelines"})


def editorial_board_page(request):
    members = EditorialBoardMember.objects.filter(is_active=True)
    return render(request, "public/editorial_board.html", {"members": members})


def contact_page(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        verified, note = verify_hcaptcha(form.cleaned_data.get("hcaptcha_token"))
        if verified:
            form.save()
            messages.success(request, "Your message has been sent successfully.")
            return redirect("contact")
        messages.error(request, note)
    return render(request, "public/contact.html", {"form": form})


def submit_paper(request):
    form = SubmissionForm(request.POST or None, request.FILES or None)
    article_id = None
    if request.method == "POST" and form.is_valid():
        submission = form.save(commit=False)
        if request.user.is_authenticated:
            submission.user = request.user
        submission.save()
        run_plagiarism_check(submission)
        create_audit_log(request.user if request.user.is_authenticated else None, "Submitted paper", "Submission", submission.article_id, submission.title)
        article_id = submission.article_id
        messages.success(request, f"Submission received. Your Article ID is {article_id}.")
        form = SubmissionForm()
    return render(request, "public/submit.html", {"form": form, "article_id": article_id})


@login_required
def submission_edit(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    
    # Permission check: either owner or admin
    is_owner = request.user.is_authenticated and submission.user == request.user
    is_admin = request.user.is_staff
    if not (is_owner or is_admin):
        messages.error(request, "You do not have permission to edit this submission.")
        return redirect("author-dashboard")
    
    # Only allow editing if submission is in draft or submitted status (for authors)
    if is_owner and submission.status not in [Submission.STATUS_DRAFT, Submission.STATUS_SUBMITTED]:
        messages.error(request, "This submission can no longer be edited.")
        return redirect("author-dashboard")
    
    form = SubmissionForm(request.POST or None, request.FILES or None, instance=submission)
    if request.method == "POST" and form.is_valid():
        submission = form.save()
        run_plagiarism_check(submission)
        create_audit_log(
            request.user,
            "Edited submission",
            "Submission",
            submission.article_id,
            f"Updated by {request.user.username}"
        )
        messages.success(request, "Submission updated successfully.")
        return redirect("author-dashboard")
    
    return render(request, "public/submit.html", {
        "form": form,
        "article_id": submission.article_id,
        "is_edit": True,
        "submission": submission
    })


def track_submission(request):
    form = StatusTrackingForm(request.GET or None)
    submission = None
    if form.is_valid() and form.cleaned_data.get("article_id"):
        submission = Submission.objects.filter(article_id=form.cleaned_data["article_id"].strip().upper()).first()
        if not submission:
            messages.error(request, "No submission found with that Article ID.")
    return render(request, "public/track.html", {"form": form, "submission": submission})


# Deprecated: account_login and account_register replaced by unified_sign_in
# Keep for backward compatibility if needed


@login_required
def account_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def author_dashboard(request):
    submissions = Submission.objects.filter(Q(user=request.user) | Q(email=request.user.email)).prefetch_related("review_assignments")
    notifications = request.user.notifications.all()[:10]
    return render(
        request,
        "public/author_dashboard.html",
        {"submissions": submissions, "notifications": notifications},
    )


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "public/profile.html", {"form": form, "profile": profile})


@role_required(UserProfile.ROLE_REVIEWER, UserProfile.ROLE_EDITOR, UserProfile.ROLE_MANAGING_EDITOR)
def reviewer_dashboard(request):
    assignments = ReviewerAssignment.objects.filter(reviewer=request.user).select_related("submission")
    return render(request, "public/reviewer_dashboard.html", {"assignments": assignments})


@login_required
def notifications_view(request):
    notifications = request.user.notifications.all()
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, "public/notifications.html", {"notifications": notifications})


def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin-dashboard")
    form = AdminLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user and user.is_staff and user.is_active:
            login(request, user)
            return redirect("admin-dashboard")
        messages.error(request, "Invalid credentials or deactivated account.")
    return render(request, "admin_portal/login.html", {"form": form})


def admin_logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("admin-login")


@super_admin_required
def admin_register_view(request):
    form = AdminUserForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_staff = True
        user.save()
        AdminProfile.objects.update_or_create(
            user=user,
            defaults={"can_manage_admins": form.cleaned_data.get("can_manage_admins", False)},
        )
        messages.success(request, "Admin account created.")
        return redirect("admin-user-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Register Admin"})


def admin_forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = resolve_user_by_email(form.cleaned_data["email"])
        if user:
            send_password_reset_otp(user)
        messages.info(request, "If the email exists, an OTP has been sent.")
        return redirect("admin-reset-password")
    return render(request, "admin_portal/forgot_password.html", {"form": form})


def admin_reset_password(request):
    form = VerifyOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = resolve_user_by_email(form.cleaned_data["email"])
        otp = None if not user else user.password_otps.filter(otp_code=form.cleaned_data["otp_code"], is_used=False).first()
        if otp and otp.is_valid:
            user.set_password(form.cleaned_data["new_password"])
            user.save()
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            messages.success(request, "Password updated successfully.")
            return redirect("admin-login")
        messages.error(request, "Invalid or expired OTP.")
    return render(request, "admin_portal/reset_password.html", {"form": form})


@staff_required
def admin_dashboard(request):
    submissions = Submission.objects.all()
    context = {
        "volume_count": Volume.objects.count(),
        "article_count": Article.objects.count(),
        "pending_submissions": submissions.filter(
            status__in=[Submission.STATUS_SUBMITTED, Submission.STATUS_SCREENING, Submission.STATUS_UNDER_REVIEW]
        ).count(),
        "active_admins": AdminSessionLog.objects.filter(is_active=True).count(),
        "recent_submissions": submissions[:5],
        "category_breakdown": Article.objects.values("category").annotate(total=Count("id")),
        "audit_logs": AuditLog.objects.all()[:8],
    }
    return render(request, "admin_portal/dashboard.html", context)


@staff_required
def volume_list(request):
    return render(request, "admin_portal/volume_list.html", {"volumes": Volume.objects.all()})


@staff_required
def volume_create(request):
    form = VolumeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Volume created.")
        return redirect("volume-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Add Volume"})


@staff_required
def volume_update(request, pk):
    volume = get_object_or_404(Volume, pk=pk)
    form = VolumeForm(request.POST or None, request.FILES or None, instance=volume)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Volume updated.")
        return redirect("volume-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Edit Volume"})


@staff_required
def volume_toggle(request, pk):
    volume = get_object_or_404(Volume, pk=pk)
    volume.is_active = not volume.is_active
    volume.save(update_fields=["is_active"])
    return redirect("volume-list")


@staff_required
def issue_create(request):
    form = IssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Issue added.")
        return redirect("volume-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Add Issue"})


@staff_required
def article_list(request):
    articles = Article.objects.select_related("volume", "issue")
    return render(request, "admin_portal/article_list.html", {"articles": articles})


@staff_required
def article_create(request):
    form = ArticleForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        article = form.save()
        assign_doi(article)
        sync_to_elasticsearch(article)
        create_audit_log(request.user, "Created article", "Article", article.pk, article.title)
        messages.success(request, "Article added.")
        return redirect("article-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Add Volume Content"})


@staff_required
def article_update(request, pk):
    article = get_object_or_404(Article, pk=pk)
    form = ArticleForm(request.POST or None, request.FILES or None, instance=article)
    if request.method == "POST" and form.is_valid():
        article = form.save()
        assign_doi(article)
        sync_to_elasticsearch(article)
        create_audit_log(request.user, "Updated article", "Article", article.pk, article.title)
        messages.success(request, "Article updated.")
        return redirect("article-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Edit Article"})


@staff_required
def article_toggle(request, pk):
    article = get_object_or_404(Article, pk=pk)
    article.is_active = not article.is_active
    article.save(update_fields=["is_active"])
    return redirect("article-list")


@staff_required
def submission_list(request):
    submissions = Submission.objects.all()
    status = request.GET.get("status")
    if status:
        submissions = submissions.filter(status=status)
    return render(request, "admin_portal/submission_list.html", {"submissions": submissions})


@staff_required
def export_submissions_csv_view(request):
    return export_submissions_csv(Submission.objects.all())


@staff_required
def export_submissions_excel_view(request):
    return export_submissions_excel(Submission.objects.all())


@staff_required
def submission_review(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    form = SubmissionReviewForm(request.POST or None, instance=submission)
    comment_form = PeerReviewCommentForm(request.POST or None)
    assignment_form = ReviewerAssignmentForm(request.POST or None)
    if request.method == "POST":
        if "save_review" in request.POST and form.is_valid():
            reviewed = form.save()
            if reviewed.status in [Submission.STATUS_ACCEPTED, Submission.STATUS_REJECTED, Submission.STATUS_PUBLISHED]:
                from django.utils import timezone
                reviewed.decision_date = timezone.now()
                reviewed.save(update_fields=["decision_date"])
                if reviewed.status == Submission.STATUS_PUBLISHED:
                    from .utils import create_article_from_submission
                    create_article_from_submission(reviewed)
            run_plagiarism_check(reviewed)
            if reviewed.user:
                create_notification(
                    reviewed.user,
                    "Submission status updated",
                    f"{reviewed.article_id} is now {reviewed.get_status_display()}",
                    f"/track/?article_id={reviewed.article_id}",
                )
            create_audit_log(request.user, "Reviewed submission", "Submission", reviewed.article_id, reviewed.status)
            messages.success(request, "Submission updated.")
            return redirect("submission-list")

        if "save_comment" in request.POST and comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.submission = submission
            comment.admin = request.user
            comment.save()
            create_audit_log(request.user, "Added peer review comment", "Submission", submission.article_id, "Comment added")
            messages.success(request, "Peer review comment added.")
            return redirect("submission-review", pk=pk)
        if "assign_reviewer" in request.POST and assignment_form.is_valid():
            assignment = assignment_form.save(commit=False)
            assignment.submission = submission
            assignment.save()
            submission.status = Submission.STATUS_UNDER_REVIEW
            submission.save(update_fields=["status"])
            create_notification(
                assignment.reviewer,
                "New review assignment",
                f"You have been assigned to review {submission.article_id}.",
                f"/reviewer/dashboard/",
            )
            create_audit_log(
                request.user,
                "Assigned reviewer",
                "Submission",
                submission.article_id,
                assignment.reviewer.username,
            )
            messages.success(request, "Reviewer assigned.")
            return redirect("submission-review", pk=pk)
    return render(
        request,
        "admin_portal/submission_review.html",
        {
            "submission": submission,
            "form": form,
            "comment_form": comment_form,
            "assignment_form": assignment_form,
            "assignments": submission.review_assignments.select_related("reviewer"),
        },
    )


@staff_required
def admin_user_list_all(request):
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    active_sessions = AdminSessionLog.objects.filter(is_active=True).select_related("user")
    if request.method == "POST":
        delete_id = request.POST.get('delete_user_id')
        if delete_id:
            user = get_object_or_404(User, pk=delete_id)
            if user == request.user:
                messages.error(request, "Cannot delete your own account.")
            else:
                username = user.username
                user.delete()
                create_audit_log(request.user, "Deleted user", "User", delete_id, username)
                messages.success(request, f"User '{username}' deleted.")
        return redirect("admin-user-list")
    
    if request.GET.get("date"):
        active_sessions = active_sessions.filter(login_time__date=request.GET["date"])
    return render(
        request,
        "admin_portal/admin_users.html",
        {"users": users, "active_sessions": active_sessions},
    )




@super_admin_required
def admin_user_create(request):
    return admin_register_view(request)


@staff_required
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "Cannot delete your own account.")
        return redirect("admin-user-list")
    
    username = user.username
    user.delete()
    create_audit_log(request.user, "Deleted user", "User", pk, username)
    messages.success(request, f"User '{username}' deleted successfully.")
    return redirect("admin-user-list")



@super_admin_required
def admin_user_edit(request, pk=None):
    if pk:
        user = get_object_or_404(User, pk=pk)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        title = "Edit User"
    else:
        user = None
        profile = None
        title = "Add User"
    
    form = UserEditForm(request.POST or None, request.FILES or None, instance=user, profile=profile)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if not pk:  # New user
            UserProfile.objects.get_or_create(user=user, defaults={'role': form.cleaned_data['role']})
        
        create_audit_log(
            request.user,
            f"{title} user account",
            "User",
            user.pk,
            f"Username: {user.username}, Role: {form.cleaned_data['role']}"
        )
        
        messages.success(request, f"User {title.lower()} successfully.")
        return redirect("admin-user-list")
    
    context = {
        "form": form, 
        "title": title,
        "user": user,
        "profile": profile
    }
    return render(request, "admin_portal/form.html", context)




@staff_required
def editorial_board_list(request):
    members = EditorialBoardMember.objects.all().order_by('order', 'name')
    if request.method == "POST":
        delete_id = request.POST.get('delete_member_id')
        if delete_id:
            member = get_object_or_404(EditorialBoardMember, pk=delete_id)
            name = member.name
            member.delete()
            create_audit_log(request.user, "Deleted board member", "EditorialBoardMember", delete_id, name)
            messages.success(request, f"Member '{name}' deleted.")
        return redirect("admin-editorial-board-list")
    return render(request, "admin_portal/editorial_board_list.html", {"members": members})


@staff_required
def editorial_board_create(request):
    form = EditorialBoardForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        member = form.save()
        create_audit_log(request.user, "Created board member", "EditorialBoardMember", member.pk, member.name)
        messages.success(request, "Board member created.")
        return redirect("admin-editorial-board-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Add Board Member"})


@staff_required
def editorial_board_edit(request, pk):
    member = get_object_or_404(EditorialBoardMember, pk=pk)
    form = EditorialBoardForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        create_audit_log(request.user, "Updated board member", "EditorialBoardMember", member.pk, member.name)
        messages.success(request, "Board member updated.")
        return redirect("admin-editorial-board-list")
    return render(request, "admin_portal/form.html", {"form": form, "title": "Edit Board Member", "member": member})


@staff_required
def editorial_board_delete(request, pk):
    member = get_object_or_404(EditorialBoardMember, pk=pk)
    name = member.name
    member.delete()
    create_audit_log(request.user, "Deleted board member", "EditorialBoardMember", pk, name)
    messages.success(request, f"Member '{name}' deleted.")
    return redirect("admin-editorial-board-list")


@role_required(UserProfile.ROLE_REVIEWER, UserProfile.ROLE_EDITOR, UserProfile.ROLE_MANAGING_EDITOR)
def reviewer_assignment_detail(request, pk):
    assignment = get_object_or_404(ReviewerAssignment, pk=pk, reviewer=request.user)
    form = ReviewerResponseForm(request.POST or None, instance=assignment)
    if request.method == "POST" and form.is_valid():
        updated = form.save()
        if updated.status == ReviewerAssignment.STATUS_COMPLETED and assignment.submission.assigned_editor:
            create_notification(
                assignment.submission.assigned_editor,
                "Review completed",
                f"{request.user.username} completed review for {assignment.submission.article_id}.",
                f"/admin/submissions/{assignment.submission.pk}/review/",
            )
        create_audit_log(request.user, "Updated review assignment", "ReviewerAssignment", updated.pk, updated.status)
        messages.success(request, "Review response saved.")
        return redirect("reviewer-dashboard")
    return render(request, "public/reviewer_assignment_detail.html", {"assignment": assignment, "form": form})
