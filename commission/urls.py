from django.urls import path
from .views import alloc_commissions  # make sure the import matches your file

urlpatterns = [
   
    path('alloc-commissions/', alloc_commissions, name='alloc_commissions'),
]
