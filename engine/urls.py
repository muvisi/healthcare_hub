# urls.py
from django.urls import path

from engine.tasks import fetch_and_push_unsynced_benefits_final, fetch_unsynced_benefit_categories_final





urlpatterns = [
    path('api/categories/', fetch_unsynced_benefit_categories_final,name='fetch_unsynced_benefit_categories_final'),
    path('api/benefits/', fetch_and_push_unsynced_benefits_final),



]