from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import ProviderRestrictionSyncFailure

from django.contrib import admin
from .models import ProviderRestrictionSyncFailure, ProviderRestrictionSyncSuccess

@admin.register(ProviderRestrictionSyncFailure)
class ProviderRestrictionSyncFailureAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "provider_code", "status_code", "created_at")
    list_filter = ("status_code", "created_at")
    search_fields = ("corp_id", "provider_code")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)


@admin.register(ProviderRestrictionSyncSuccess)
class ProviderRestrictionSyncSuccessAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "provider_code", "status_code", "created_at")
    list_filter = ("status_code", "created_at")
    search_fields = ("corp_id", "provider_code")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)
    
    from django.contrib import admin
from .models import WaitingPeriodSyncFailure

@admin.register(WaitingPeriodSyncFailure)
class WaitingPeriodSyncFailureAdmin(admin.ModelAdmin):
    list_display = (
        "scheme_id",
        "family_no",
        "benefit",
        "anniv",
        "status_code",
        "created_at",
    )
    search_fields = ("scheme_id", "family_no", "benefit")
    list_filter = ("status_code", "created_at")
    
    from django.contrib import admin
from .models import WaitingPeriodSyncSuccess

@admin.register(WaitingPeriodSyncSuccess)
class WaitingPeriodSyncSuccessAdmin(admin.ModelAdmin):
    list_display = (
        "scheme_id",
        "family_no",
        "benefit",
        "anniv",
        "status_code",
        "created_at",
    )
    list_filter = ("status_code", "created_at")
    search_fields = ("scheme_id", "family_no", "benefit", "anniv")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)

from .models import HaisCategorySyncSuccess, HaisCategorySyncFailure

@admin.register(HaisCategorySyncSuccess)
class HaisCategorySyncSuccessAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "category_name", "anniv", "status_code", "created_at")
    list_filter = ("status_code", "created_at")
    search_fields = ("corp_id", "category_name")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)


@admin.register(HaisCategorySyncFailure)
class HaisCategorySyncFailureAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "category_name", "anniv", "status_code", "created_at")
    list_filter = ("status_code", "created_at")
    search_fields = ("corp_id", "category_name")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)
    
    
from django.contrib import admin
from .models import BenefitSyncSuccess, BenefitSyncFailure

@admin.register(BenefitSyncSuccess)
class BenefitSyncSuccessAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "benefit_id", "benefit_name", "policy_no", "category", "anniv", "smart_status", "created_at")
    list_filter = ("smart_status", "created_at")
    search_fields = ("corp_id", "benefit_id", "benefit_name")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)


@admin.register(BenefitSyncFailure)
class BenefitSyncFailureAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "benefit_id", "benefit_name", "policy_no", "category", "anniv", "smart_status", "created_at")
    list_filter = ("smart_status", "created_at")
    search_fields = ("corp_id", "benefit_id", "benefit_name")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)
    
from django.contrib import admin
from .models import MemberSyncSuccess, MemberSyncFailure

@admin.register(MemberSyncSuccess)
class MemberSyncSuccessAdmin(admin.ModelAdmin):
    list_display = ("member_no", "surname", "family_no", "corp_id", "category", "anniv", "smart_status", "created_at")
    list_filter = ("smart_status", "created_at")
    search_fields = ("member_no", "surname", "family_no")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)

@admin.register(MemberSyncFailure)
class MemberSyncFailureAdmin(admin.ModelAdmin):
    list_display = ("member_no", "surname", "family_no", "corp_id", "category", "anniv", "smart_status", "created_at")
    list_filter = ("smart_status", "created_at")
    search_fields = ("member_no", "surname", "family_no")
    readonly_fields = ("created_at", "smart_response")
    ordering = ("-created_at",)
    
    
from django.contrib import admin
from .models import ApiSyncLog

@admin.register(ApiSyncLog)
class ApiSyncLogAdmin(admin.ModelAdmin):
    list_display = ("api_name", "transaction_name", "status", "http_code", "created_at")
    list_filter = ("api_name", "transaction_name", "status", "created_at")
    search_fields = ("api_name", "transaction_name", "request_object", "response_object")
    readonly_fields = ("api_name", "transaction_name", "request_object", "response_object", "status", "http_code", "created_at")
    
# from django.contrib import admin
from .models import CopayLog

@admin.register(CopayLog)
class CopayLogAdmin(admin.ModelAdmin):
    list_display = ('transaction_name', 'status', 'status_code', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('transaction_name', 'source')
    readonly_fields = ('created_at', 'updated_at')