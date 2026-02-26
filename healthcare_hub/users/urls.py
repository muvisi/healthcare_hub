from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginAPIView, UsersViewSet

router = DefaultRouter()
router.register(r'users', UsersViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path("login/", LoginAPIView.as_view(), name="login"),

]