from celery import shared_task

from jobs.benefits import SyncHaisBenefitsService, SyncHaisRetailBenefitsService
from jobs.categories import SyncHaisCategoriesService, SyncRetailCategoriesService
from jobs.copays import SyncHaisCopaysService
from jobs.members import SyncHaisMembersService, SyncRetailMembersService
from jobs.restrictions import SyncProviderRestrictionsService
from jobs.waiting_periods import SyncHaisRetailWaitingPeriodsService

@shared_task(bind=True)
def say_hi(self):
    print("Hi! Celery job is running")
    return "Printed Hi"


@shared_task(bind=True)
def sync_benefits_job(self):
    service = SyncHaisBenefitsService()
    service.run()
    print("HAIS corporate benefits sync job executed")
    


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_retail_benefits_job(self):
    service = SyncHaisRetailBenefitsService()
    service.run()
    print("HAIS Retail benefits sync job executed")
    
    

@shared_task(bind=True)
def sync_members_job(self):
    service = SyncHaisMembersService()
    service.run()
    print("HAIS corporate members sync job executed")
    

@shared_task
def sync_retail_members_job():
    service = SyncRetailMembersService()
    service.run()
    print("HAIS retail members sync job executed")
    
@shared_task
def sync_categories_job():
    service = SyncHaisCategoriesService()
    service.run()
    
@shared_task
def sync_retail_categories_job():
    service = SyncRetailCategoriesService()
    service.run()
    
    
@shared_task
def sync_provider_restrictions_job():
    service = SyncProviderRestrictionsService()
    service.run()
    
    
@shared_task
def sync_waiting_periods_job():
    service=SyncHaisRetailWaitingPeriodsService()
    service.run()
    
    
@shared_task
def sync_hais_copays_job():
    service = SyncHaisCopaysService()
    service.run()