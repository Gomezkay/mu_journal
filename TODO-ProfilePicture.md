# User Profile Picture + Edit Fix (Active)

**Status**: Planning → Implementation  
**Approved**: Yes (with user.png placeholder)

## Steps:
- [x] 1. Update journal/models.py: Add profile_picture ImageField to UserProfile (upload_to='profiles/')\n- [x] 2. python manage.py makemigrations journal && python manage.py migrate
- [x] 3. Update journal/forms.py: Add profile_picture field + save logic to UserEditForm, ProfileForm, AdminUserForm
- [ ] 4. Enhance templates/public/profile.html: Custom form with image preview (user.png fallback), styled upload
- [ ] 5. Update templates/admin_portal/form.html: Add profile pic preview block
- [ ] 6. Update templates/admin_portal/admin_users.html: Add profile pic thumbnail column with user.png fallback
- [ ] 7. Add CSS to static/css/site.css: .profile-preview styles
- [ ] 8. Test: Admin add/edit user picture upload/save/display. Public profile edit same. Fallback works.
- [ ] 9. Optional: Add thumbnail to journal/admin.py User admin
- [ ] 10. Complete → attempt_completion

**Notes**: 
- Placeholder: static/images/user.png
- Test media serving

