# urls.py
from django.urls import path

from smart.categories import fetch_unsynced_corp_groups
from smart.schemes import fetch_new_schemes

# from retail_members.sync_members import remote_corporate_api
# from .views import remote_users_api, sync_members_api

urlpatterns = [
    # path('api/remote-users/', remote_users_api),
    path('api/fetch_new_schemes/', fetch_new_schemes, name='fetch_new_schemes'),
    path('api/fetch-corp-groups/', fetch_unsynced_corp_groups),

    # path("api/remote-corporate/", remote_corporate_api),


]