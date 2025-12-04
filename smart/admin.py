from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Corporate

@admin.register(Corporate)
class CorporateAdmin(admin.ModelAdmin):
    list_display = (
        "clnCode",
        "companyName",
        "clnPolCode",
        "anniv",
        "userId",
        "policyNumber",
        "cancelled",
        "synced",
        "created_at",
    )
    list_filter = ("cancelled", "synced", "anniv", "countryCode")
    search_fields = ("clnCode", "companyName", "policyNumber", "userId")
    ordering = ("-created_at",)


from django.contrib import admin
from .models import BenefitCategory


@admin.register(BenefitCategory)
class BenefitCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "idx",
        "catDesc",
        "clnCatCode",
        "clnPolCode",
        "country",
        "userId",
        "synced",
        "created_at",
        "updated_at",
    )

    list_filter = ("synced", "country", "created_at")
    search_fields = ("catDesc", "clnCatCode", "clnPolCode")
    ordering = ("-created_at",)


from django.contrib import admin
from .models import Benefit


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = (
        "idx",
        "clnPolCode",
        "CatCode",
        "clnBenCode",
        "benefitDesc",
        "benTypeId",
        "subLimitAmt",
        "serviceType",
        "synced",
        "updated_at",
    )

    list_filter = ("synced", "CatCode", "clnPolCode")
    search_fields = ("clnBenCode", "benefitDesc", "clnPolCode", "CatCode")
    ordering = ("-updated_at",)
