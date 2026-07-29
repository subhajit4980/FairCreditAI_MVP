from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    AAConsent,
    AuditLog,
    BankStatement,
    CustomerProfile,
    Document,
    ScoreReport,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("FairCredit", {"fields": ("role", "mobile", "pan")}),
    )


admin.site.register(CustomerProfile)
admin.site.register(Document)
admin.site.register(AAConsent)
admin.site.register(ScoreReport)
admin.site.register(BankStatement)
admin.site.register(AuditLog)
