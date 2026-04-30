from django.urls import path
from .views import CommissionRecordsView

urlpatterns = [
    path('records/', CommissionRecordsView.as_view(), name='commission-records'),
]
