
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_hub.settings')

app = Celery('healthcare_hub')

app.config_from_object('django.conf:settings', namespace='CELERY')

# app.autodiscover_tasks()

# Move Beat Schedule here instead of settings.py
# app.conf.beat_schedule = {
#     'sync_corporates_every_hour': {
#         'task': 'retail_members.email.send_test_email',
#         'schedule': crontab(minute='*'),
#     },
# }
# app.conf.beat_schedule = {
#     'sync_schemes_every_minute': {
#         'task': 'smart.schemes.fetch_new_schemes',
#         'schedule': crontab(minute='*'),
#     },
# }
# app.conf.beat_schedule = {
#     'sync_schemes_every_minute': {
#         'task': 'smart.categories.fetch_unsynced_benefit_categories',
#         'schedule': crontab(minute='*'),
#     },
# }
# app.conf.beat_schedule = {
#     'sync_benefits_every_minute': {
#         'task': 'smart.benefits.tasks.fetch_unsynced_benefits_task',
#         'schedule': crontab(minute='*'),
#     },
# }
app.autodiscover_tasks(['smart', 'retail_members'])

app.conf.beat_schedule = {
    'sync_benefits_every_minute': {
        'task': 'smart.benefits.fetch_unsynced_benefits_task',
        'schedule': crontab(minute='*'),
    },
}