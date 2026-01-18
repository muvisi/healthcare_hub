# app/tasks.py
from celery import shared_task
from datetime import datetime
from django.utils.timezone import localtime
from .views import alloc_commissions  # reuse your allocation function
from django.test import RequestFactory

@shared_task
def daily_allocation_task():
    now_dt = datetime.now()
    day = now_dt.day

    # Skip 16,17,18 and 1,2,3 of each month
    if day in [1,2,3,16,17]:
        print(f"Allocation skipped on {now_dt.strftime('%d-%b-%Y')}")
        return "Skipped"

    # Simulate a GET request for the allocation view
    factory = RequestFactory()
    request = factory.get("/commissions/alloc-commissions/")
    response = alloc_commissions(request)
    print("Allocation executed at 5 PM")
    return "Completed"
