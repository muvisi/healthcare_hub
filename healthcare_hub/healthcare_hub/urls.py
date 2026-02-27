
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('engine/', include('engine.urls')),
    path('api/account/', include('users.urls')),  # Users CRUD APIs
    path("api/trigger/", include("trigger.urls")),
    path('api/report/', include('reports.urls')),  # 👈 register report app here



    # path('smart/', include('smart.urls')),
    # path('smart-engine/', include('engine.urls')),
    # path('commissions/', include('commission.urls')),



]