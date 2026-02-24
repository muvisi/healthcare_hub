
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('engine/', include('engine.urls')),
    # path('smart/', include('smart.urls')),
    # path('smart-engine/', include('engine.urls')),
    # path('commissions/', include('commission.urls')),



]