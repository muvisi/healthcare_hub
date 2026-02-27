# report/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('provider-failure/', ProviderRestrictionSyncFailureListView.as_view(), name='provider-failure'),
    path('provider-success/', ProviderRestrictionSyncSuccessListView.as_view(), name='provider-success'),
    path('waiting-failure/', WaitingPeriodSyncFailureListView.as_view(), name='waiting-failure'),
    path('waiting-success/', WaitingPeriodSyncSuccessListView.as_view(), name='waiting-success'),
    path('hais-category-failure/', HaisCategorySyncFailureListView.as_view(), name='category-failure'),
    path('hais-category-success/', HaisCategorySyncSuccessListView.as_view(), name='category-success'),
    path('benefit-failure/', BenefitSyncFailureListView.as_view(), name='benefit-failure'),
    path('benefit-success/', BenefitSyncSuccessListView.as_view(), name='benefit-success'),
    path('member-failure/', MemberSyncFailureListView.as_view(), name='member-failure'),
    path('member-success/', MemberSyncSuccessListView.as_view(), name='member-success'),
    path('api-sync/', ApiSyncLogListView.as_view(), name='api-sync'),
    path('copay/', CopayLogListView.as_view(), name='copay-log'),
]

