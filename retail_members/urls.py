# urls.py
from django.urls import path

from retail_members.sync_members import remote_corporate_api
from .views import remote_users_api, sync_members_api

urlpatterns = [
    path('api/remote-users/', remote_users_api),
    path('api/sync-members/', sync_members_api, name='sync-members'),
    path("api/remote-corporate/", remote_corporate_api),


]
