from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_hub.settings')

app = Celery('healthcare_hub')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks from your commission app
app.autodiscover_tasks(['commission'])

# ===============================
# CELERY BEAT SCHEDULE
# ===============================
# Run every day at 5 PM
app.conf.beat_schedule = {
    "daily_allocation_5pm": {
        "task": "commission.tasks.daily_allocation_task",  # make sure 'commission' matches your app folder name
        "schedule": crontab(hour=17, minute=0),
        "args": (),  # no arguments needed
    },
}


# app.conf.beat_schedule = {
#     "daily_allocation_test_every_minute": {
#         "task": "commission.tasks.daily_allocation_task",  # your task path
#         "schedule": 60.0,  # 60 seconds = every 1 minute
#         "args": (),  # no arguments needed
#     },
# }

# Optional: Debug task
@app.task(bind=True)
def debug_task(self):
    print(f"Celery debug task running: {self.request}")
