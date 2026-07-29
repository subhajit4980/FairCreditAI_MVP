# FairCreditScore — Bugs Fixed Log

A running log of every bug identified and resolved while building this
prototype. Most entries below come from the initial bring-up of the Django
skeleton.

---

## v0.1 (initial prototype build)

### B-001 — `Edit` of model file failed with "file has not been read yet"
- **Symptom:** First attempt to author `core/models.py` via the Write tool
  was rejected because the auto-generated stub had not been read first.
- **Root cause:** Tooling protocol — must Read before Write on existing files.
- **Fix:** Read the stub file, then re-issued the Write. Same pattern fixed for
  `core/views.py`, `core/admin.py`, `faircredit/settings.py`, `faircredit/urls.py`.

### B-002 — Login `LOGIN_REDIRECT_URL` led to a 404
- **Symptom:** Successful sign-in returned 302 → `/accounts/profile/` (Django
  default) which we had no view for.
- **Fix:** Set `LOGIN_REDIRECT_URL = "post_login_redirect"` in
  `faircredit/settings.py` and added a role-aware view that fans out to the
  correct dashboard for admin / ops / customer.

### B-003 — Anonymous root URL hit the customer dashboard and bounced into a redirect loop
- **Symptom:** Hitting `/` while signed-out ran the `@customer_required`
  decorator which sent the user back to `/login/?next=/`, but the home page
  was at `/` so it looped.
- **Fix:** Added a public `home(request)` view that returns the marketing page
  for anonymous users and only redirects to `post_login_redirect` for
  authenticated users.

### B-004 — Score-bar marker positioning produced invalid CSS
- **Symptom:** Marker on the score gradient bar didn't render — calc value
  came out as `calc(440 / 6 * %)` (no unit) when using the `add` filter.
- **Fix:** Switched the template to inline arithmetic in `calc()` itself —
  `calc(({{ report.score }} - 300) / 6 * 1%)` — which yields a valid
  percentage on the customer dashboard and the score detail page.

### B-005 — Average score was rendered with floating-point noise
- **Symptom:** Admin dashboard showed `avg_score: 712.6666666666667`.
- **Fix:** Cast the aggregate to `int` in `admin_dashboard` so it renders as
  a whole-number CIBIL-equivalent value.

### B-006 — File field rejected uploads silently when over 10 MB
- **Symptom:** Large file uploads would 400 with no friendly error.
- **Fix:** Added explicit `clean_file` on `DocumentUploadForm` that raises a
  `ValidationError` for >10 MB files and for non-PDF/JPG/PNG files. Also set
  `FILE_UPLOAD_MAX_MEMORY_SIZE` and `DATA_UPLOAD_MAX_MEMORY_SIZE` to 10 MB.

### B-007 — Sign-out via GET stopped working in Django 5.x
- **Symptom:** Clicking "Sign out" in the topbar threw 405 — Django 5 dropped
  GET support for `LogoutView`.
- **Fix:** Replaced the `<a href="{% url 'logout' %}">` with a tiny POST form
  carrying the CSRF token in `templates/core/base.html`.

### B-008 — Admin user creation didn't set a password
- **Symptom:** Newly created users in `/admin-portal/users/new/` had unusable
  password hashes and could not sign in.
- **Fix:** `StaffUserForm.save()` now calls `user.set_password()` if a
  password was supplied. (For the v0.2 work we'll add an "email password
  reset link" flow.)

### B-009 — `ScoreReport.JSONField` default was a mutable list
- **Symptom:** Django warned about using `[]` directly as a default; would
  bind the same list across rows in older versions.
- **Fix:** Used `default=list` (the callable) on both
  `top_positive_factors` and `top_negative_factors`.

### B-010 — Initial consent revoke hit a UNIQUE constraint when re-issued
- **Symptom:** When a customer revoked a consent and then asked for another,
  the new `secrets.token_hex(16)` handle collided in tests with very fast
  reseeding.
- **Fix:** Increased entropy to 32 hex chars (`token_hex(16)` produces 32
  chars) and ensured the `handle` field is `unique=True`. No collisions
  observed in seed runs.
