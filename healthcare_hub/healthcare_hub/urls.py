from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('engine/', include('engine.urls')),
    path('api/account/', include('users.urls')),  # Users CRUD APIs
    path("api/trigger/", include("trigger.urls")),
    path('api/report/', include('reports.urls')),  # 👈 register report app here
    path('commissions/', include('commissions.urls')),



    # path('smart/', include('smart.urls')),
    # path('smart-engine/', include('engine.urls')),
    # path('commissions/', include('commission.urls')),

    # OpenAPI schema (JSON/YAML)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # ReDoc UI (an alternative, also supported)
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),



]