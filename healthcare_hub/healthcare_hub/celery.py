# healthcare_hub/celery.py
import os
from celery import Celery
from datetime import timedelta

# --- Set Django settings module ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "healthcare_hub.settings")

# --- Create Celery app ---
app = Celery("healthcare_hub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# --- Debug task to test Celery setup ---
@app.task(bind=True)
def debug_task(self):
    print(f"Celery debug task running: {self.request}")

# --- Beat schedule for periodic tasks ---
app.conf.beat_schedule = {
   
    "sync_benefits_every_2_min": {
        "task": "jobs.tasks.sync_benefits_job",
        "schedule": timedelta(minutes=2),
        "args": (),
    },

    
    "sync_retail_benefits_every_2_min": {
        "task": "jobs.tasks.sync_retail_benefits_job",
        "schedule": timedelta(minutes=2),
        "args": (),
    },
     "sync_members_every_2_min": {
        "task": "jobs.tasks.sync_members_job",
        "schedule": timedelta(minutes=1),
        "args": (),
    },
     "sync_retail_members_every_2_min": {
        "task": "jobs.tasks.sync_retail_members_job",
        "schedule": timedelta(minutes=1),
    },
     "sync_categories_every_2_min": {
    "task": "jobs.tasks.sync_categories_job",
    "schedule": timedelta(minutes=2),
    },
    "sync_retail_categories_every_2_min": {
    "task": "jobs.tasks.sync_retail_categories_job",
    "schedule": timedelta(minutes=1),
},
    "sync_provider_restrictions_every_2_min": {
    "task": "jobs.tasks.sync_provider_restrictions_job",
    "schedule": timedelta(minutes=2),
},
    "sync_waiting_periods_every_2_min": {
        "task": "jobs.tasks.sync_waiting_periods_job",
        "schedule": timedelta(minutes=2),
    },
     'sync-copays-every-5-minutes': {
        'task': 'engine.tasks.sync_hais_copays_job',  
        'schedule': timedelta(minutes=5), 
    },
    
}


app.conf.timezone = "Africa/Nairobi"

