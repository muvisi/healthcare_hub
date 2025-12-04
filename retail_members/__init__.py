from healthcare_hub.celery import app as celery_app
from . import email

__all__ = ('celery_app',)
