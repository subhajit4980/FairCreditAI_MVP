from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("post-login/", views.post_login_redirect, name="post_login_redirect"),

    # Customer
    path("me/", views.customer_dashboard, name="customer_dashboard"),
    path("me/profile/", views.customer_profile, name="customer_profile"),
    path("me/documents/upload/", views.upload_document, name="upload_document"),
    path("me/bank-statement/upload/", views.upload_bank_statement, name="upload_bank_statement"),
    path("me/consent/initiate/", views.initiate_consent, name="initiate_consent"),
    path("me/fetch-aa/callback/", views.customer_aa_callback, name="customer_aa_callback"),
    path("me/consent/<str:handle>/", views.consent_review, name="consent_review"),
    path("me/consent/<str:handle>/approve/", views.consent_approve, name="consent_approve"),
    path("me/consent/<str:handle>/revoke/", views.consent_revoke, name="consent_revoke"),
    path("me/score/generate/", views.generate_my_score, name="generate_my_score"),
    path("me/score/<int:pk>/", views.score_detail, name="score_detail"),
    path("me/score/<int:pk>/download-transactions/", views.download_aa_transactions, name="download_aa_transactions"),

    # Operations
    path("ops/", views.ops_dashboard, name="ops_dashboard"),
    path("ops/documents/", views.ops_documents, name="ops_documents"),
    path("ops/documents/<int:pk>/review/", views.ops_review_document, name="ops_review_document"),
    path("ops/customers/", views.ops_customers, name="ops_customers"),
    path("ops/customers/new/", views.ops_create_customer, name="ops_create_customer"),
    path("ops/customers/<int:pk>/", views.ops_customer_detail, name="ops_customer_detail"),
    path("ops/customers/<int:pk>/profile/edit/", views.ops_edit_customer_profile, name="ops_edit_customer_profile"),
    path("ops/customers/<int:pk>/bank-statement/upload/", views.ops_upload_bank_statement, name="ops_upload_bank_statement"),
    path("ops/customers/<int:pk>/fetch-aa/", views.ops_fetch_aa, name="ops_fetch_aa"),
    path("ops/customers/<int:pk>/fetch-aa/callback/", views.ops_aa_callback, name="ops_aa_callback"),
    path("ops/customers/<int:pk>/generate-score/", views.ops_generate_score, name="ops_generate_score"),

    # Administrator
    path("admin-portal/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-portal/users/", views.admin_users, name="admin_users"),
    path("admin-portal/users/new/", views.admin_user_edit, name="admin_user_create"),
    path("admin-portal/users/<int:pk>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("admin-portal/audit/", views.admin_audit, name="admin_audit"),
    path("admin-portal/wiki/", views.admin_wiki, name="admin_wiki"),
    path("admin-portal/wiki/raw/<path:rel_path>", views.admin_wiki_raw, name="admin_wiki_raw"),
    path("admin-portal/wiki/<path:rel_path>", views.admin_wiki, name="admin_wiki_node"),

    # Lender API mock
    path("api/lender/score/<int:customer_id>/", views.lender_api_score, name="lender_api_score"),
]
