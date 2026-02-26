# trigger/urls.py
from django.urls import path
from .views import TriggerSectionAPIView

urlpatterns = [
    path("trigger/", TriggerSectionAPIView.as_view(), name="trigger-section"),
]