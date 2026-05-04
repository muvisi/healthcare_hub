from django.urls import path
from .views import CommissionRecordsView, DetailedCommissionRecordsView

urlpatterns = [
    path('records/', CommissionRecordsView.as_view(), name='commission-records'),
    path('detailed-records/', DetailedCommissionRecordsView.as_view(), name='detailed-commission-records'),
]
