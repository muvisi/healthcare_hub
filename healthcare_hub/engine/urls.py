from django.urls import path

from engine.corpbenefits import SyncHaisBenefitsView
from engine.corpmemberrenewal import SyncMemberRenewalsView
from engine.corpmembers import SyncHaisMembersView
from engine.corporatecategories import SyncHaisCategoriesView
from engine.memberdetailschange import SyncMemberChangesView
from engine.providerrestrictions import SyncProviderRestrictionsView
from engine.retailbenefit import SyncBenefitsView
from engine.retailcategories import SyncRetailCategoriesView
from engine.retailmembers import SyncMembersView
from engine.retailwaitingperiods import SyncWaitingPeriodsView
from engine.schemerenewal import SyncRenewedSchemesView
from engine.schemes import SyncHaisToSmartView
from engine.schemescopays import SyncHaisCopaysView
from engine.corpwaitingperiod import SyncHaisWaitingPeriodsView
from engine.tokens import GetSmartTokenView

urlpatterns = [
        path("token/smart/", GetSmartTokenView.as_view(), name="get_smart_token"),

    
    path("push-schemes", SyncHaisToSmartView.as_view(), name="sync-schemes"),
    path("corporate-categories", SyncHaisCategoriesView.as_view(), name="sync-categories"),
    path("corporate-benefits", SyncHaisBenefitsView.as_view(), name="sync-benefits"),
    path("corporate-members", SyncHaisMembersView.as_view(), name="sync-members"),
    path("schemes-copay", SyncHaisCopaysView.as_view(), name="sync-copays"),
    path("push-waiting-periods", SyncHaisWaitingPeriodsView.as_view(), name="sync-waiting-periods"),
    path("push-renewed-schemes", SyncRenewedSchemesView.as_view(), name="sync-renewed-schemes"),
    path("push-member-changes", SyncMemberChangesView.as_view(), name="sync-member-changes"),
    path("push-member-renewals", SyncMemberRenewalsView.as_view(), name="sync-member-renewals"),
    path("push-provider-restrictions", SyncProviderRestrictionsView.as_view(), name="sync-provider-restrictions"),
    path('push-retail-categories', SyncRetailCategoriesView.as_view(), name='sync-retail-categories'),
    path("push-retail-benefits", SyncBenefitsView.as_view(), name="sync-benefits"),
    path("push-retail-members", SyncMembersView.as_view(), name="sync-members"),
    path("retail-waiting-periods", SyncWaitingPeriodsView.as_view(), name="sync-waiting-periods"),
    path("retail-member-renewals/", SyncMemberRenewalsView.as_view(), name="sync-member-renewals"),











]


