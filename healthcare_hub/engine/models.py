# # in your app's models.py
# from django.db import models

# class ProviderRestrictionSyncFailure(models.Model):
#     corp_id = models.CharField(max_length=50)
#     provider_code = models.CharField(max_length=50)
#     smart_restriction_category = models.JSONField()
#     user_id = models.CharField(max_length=50, null=True, blank=True)
#     status_code = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.corp_id} - {self.provider_code} - {self.status_code}"
    
    
# class ProviderRestrictionSyncSuccess(models.Model):
#     corp_id = models.CharField(max_length=50)
#     provider_code = models.CharField(max_length=50)
#     smart_restriction_category = models.CharField(max_length=100)
#     user_id = models.CharField(max_length=50, null=True, blank=True)
#     status_code = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.corp_id} - {self.provider_code}"
    
    
    
# class WaitingPeriodSyncFailure(models.Model):
#     scheme_id = models.CharField(max_length=50)
#     family_no = models.CharField(max_length=50)
#     category = models.CharField(max_length=100)
#     benefit = models.CharField(max_length=100)
#     anniv = models.CharField(max_length=50)
#     status_code = models.IntegerField()
#     smart_response = models.JSONField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.scheme_id} - {self.family_no} - {self.benefit}"
    
    
# class WaitingPeriodSyncSuccess(models.Model):
#     scheme_id = models.CharField(max_length=50)
#     family_no = models.CharField(max_length=50)
#     benefit = models.CharField(max_length=50)
#     anniv = models.CharField(max_length=50)
#     status_code = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)
    
    







# class HaisCategorySyncSuccess(models.Model):
#     corp_id = models.CharField(max_length=50)
#     category_name = models.CharField(max_length=100)
#     anniv = models.CharField(max_length=10)
#     user_id = models.CharField(max_length=50)
#     status_code = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.corp_id} - {self.category_name}"


# class HaisCategorySyncFailure(models.Model):
#     corp_id = models.CharField(max_length=50)
#     category_name = models.CharField(max_length=100)
#     anniv = models.CharField(max_length=10)
#     user_id = models.CharField(max_length=50)
#     status_code = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.corp_id} - {self.category_name}"
    
    


# class BenefitSyncSuccess(models.Model):
#     corp_id = models.CharField(max_length=50)
#     category = models.CharField(max_length=50)
#     anniv = models.CharField(max_length=10)
#     benefit_id = models.CharField(max_length=50)
#     benefit_name = models.CharField(max_length=100)
#     policy_no = models.CharField(max_length=50)
#     smart_status = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.corp_id} - {self.benefit_id}"


# class BenefitSyncFailure(models.Model):
#     corp_id = models.CharField(max_length=50)
#     category = models.CharField(max_length=50)
#     anniv = models.CharField(max_length=10)
#     benefit_id = models.CharField(max_length=50)
#     benefit_name = models.CharField(max_length=100)
#     policy_no = models.CharField(max_length=50)
#     smart_status = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.corp_id} - {self.benefit_id}"
    
    
    

# class MemberSyncSuccess(models.Model):
#     member_no = models.CharField(max_length=50)
#     family_no = models.CharField(max_length=50)
#     surname = models.CharField(max_length=50)
#     second_name = models.CharField(max_length=50, blank=True)
#     third_name = models.CharField(max_length=50, blank=True)
#     other_names = models.CharField(max_length=50, default="null")
#     category = models.CharField(max_length=50)
#     anniv = models.CharField(max_length=10)
#     corp_id = models.CharField(max_length=50)
#     smart_status = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.member_no} - {self.surname}"


# class MemberSyncFailure(models.Model):
#     member_no = models.CharField(max_length=50)
#     family_no = models.CharField(max_length=50)
#     surname = models.CharField(max_length=50)
#     second_name = models.CharField(max_length=50, blank=True)
#     third_name = models.CharField(max_length=50, blank=True)
#     other_names = models.CharField(max_length=50, default="null")
#     category = models.CharField(max_length=50)
#     anniv = models.CharField(max_length=10)
#     corp_id = models.CharField(max_length=50)
#     smart_status = models.IntegerField()
#     smart_response = models.JSONField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.member_no} - {self.surname}"
    
    
#     from django.db import models
# from django.utils import timezone

# class ApiSyncLog(models.Model):
#     STATUS_CHOICES = (
#         (1, "Success"),
#         (2, "Failure"),
#     )

#     api_name = models.CharField(max_length=255)  # e.g., SyncHaisToSmart
#     transaction_name = models.CharField(max_length=255)  # e.g., Corporate Scheme
#     request_object = models.JSONField(null=True, blank=True)
#     response_object = models.JSONField(null=True, blank=True)
#     status = models.IntegerField(choices=STATUS_CHOICES)
#     http_code = models.IntegerField(null=True, blank=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         verbose_name = "API Sync Log"
#         verbose_name_plural = "API Sync Logs"

#     def __str__(self):
#         return f"{self.api_name} - {self.transaction_name} - {'Success' if self.status == 1 else 'Failure'}"


import uuid
from django.db import models
from django.utils import timezone


from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class User(models.Model):
    user_id = models.BigAutoField(primary_key=True)
    user_name = models.CharField(max_length=100, unique=True)
    full_names = models.CharField(max_length=150, null=True, blank=True)
    user_pass = models.CharField(max_length=255)
    blocked = models.BooleanField(default=False)
    next_login = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_password(self, raw_password):
        self.user_pass = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.user_pass)

    def __str__(self):
        return self.user_name

# ------------------------------
# Provider Restriction Sync
# ------------------------------
class ProviderRestrictionSyncFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corp_id = models.CharField(max_length=50)
    provider_code = models.CharField(max_length=50)
    smart_restriction_category = models.JSONField()
    user_id = models.CharField(max_length=50, null=True, blank=True)
    status_code = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.corp_id} - {self.provider_code} - {self.status_code}"


class ProviderRestrictionSyncSuccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corp_id = models.CharField(max_length=50)
    provider_code = models.CharField(max_length=50)
    smart_restriction_category = models.CharField(max_length=100)
    user_id = models.CharField(max_length=50, null=True, blank=True)
    status_code = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.corp_id} - {self.provider_code}"


# ------------------------------
# Waiting Period Sync
# ------------------------------
class WaitingPeriodSyncFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_id = models.CharField(max_length=50)
    family_no = models.CharField(max_length=50)
    category = models.CharField(max_length=100)
    benefit = models.CharField(max_length=100)
    anniv = models.CharField(max_length=50)
    status_code = models.IntegerField()
    smart_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.scheme_id} - {self.family_no} - {self.benefit}"


class WaitingPeriodSyncSuccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_id = models.CharField(max_length=50)
    family_no = models.CharField(max_length=50)
    benefit = models.CharField(max_length=50)
    anniv = models.CharField(max_length=50)
    status_code = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


# ------------------------------
# Category Sync
# ------------------------------
class HaisCategorySyncSuccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corp_id = models.CharField(max_length=50)
    category_name = models.CharField(max_length=100)
    anniv = models.CharField(max_length=10)
    user_id = models.CharField(max_length=50)
    status_code = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.corp_id} - {self.category_name}"


class HaisCategorySyncFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corp_id = models.CharField(max_length=50)
    category_name = models.CharField(max_length=100)
    anniv = models.CharField(max_length=10)
    user_id = models.CharField(max_length=50)
    status_code = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.corp_id} - {self.category_name}"


# ------------------------------
# Benefit Sync
# ------------------------------
class BenefitSyncSuccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corp_id = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    anniv = models.CharField(max_length=10)
    benefit_id = models.CharField(max_length=50)
    benefit_name = models.CharField(max_length=100)
    policy_no = models.CharField(max_length=50)
    smart_status = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.corp_id} - {self.benefit_id}"


class BenefitSyncFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corp_id = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    anniv = models.CharField(max_length=10)
    benefit_id = models.CharField(max_length=50)
    benefit_name = models.CharField(max_length=100)
    policy_no = models.CharField(max_length=50)
    smart_status = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.corp_id} - {self.benefit_id}"


# ------------------------------
# Member Sync
# ------------------------------
class MemberSyncSuccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member_no = models.CharField(max_length=50)
    family_no = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    second_name = models.CharField(max_length=50, blank=True)
    third_name = models.CharField(max_length=50, blank=True)
    other_names = models.CharField(max_length=50, default="null")
    category = models.CharField(max_length=50)
    anniv = models.CharField(max_length=10)
    corp_id = models.CharField(max_length=50)
    smart_status = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member_no} - {self.surname}"


class MemberSyncFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member_no = models.CharField(max_length=50)
    family_no = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    second_name = models.CharField(max_length=50, blank=True)
    third_name = models.CharField(max_length=50, blank=True)
    other_names = models.CharField(max_length=50, default="null")
    category = models.CharField(max_length=50)
    anniv = models.CharField(max_length=10)
    corp_id = models.CharField(max_length=50)
    smart_status = models.IntegerField()
    smart_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member_no} - {self.surname}"


# ------------------------------
# API Sync Log
# ------------------------------
class ApiSyncLog(models.Model):
    STATUS_CHOICES = (
        (1, "Success"),
        (2, "Failure"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api_name = models.CharField(max_length=255)  # e.g., SyncHaisToSmart
    transaction_name = models.CharField(max_length=255)  # e.g., Corporate Scheme
    request_object = models.JSONField(null=True, blank=True)
    response_object = models.JSONField(null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES)
    http_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "schemes Api Logs"
        verbose_name_plural = "schemes Api Logs"

    def __str__(self):
        return f"{self.api_name} - {self.transaction_name} - {'Success' if self.status == 1 else 'Failure'}"
    
    
from django.db import models
from django.utils import timezone

class CopayLog(models.Model):
    STATUS_CHOICES = [
        (1, 'Success'),
        (2, 'Failure'),
    ]

    source = models.CharField(max_length=50, default='HAIS-SMART')
    transaction_name = models.CharField(max_length=100, default='Corporate Scheme Copay')
    status_code = models.PositiveIntegerField()
    request_object = models.JSONField(null=True, blank=True)   # Updated
    response_object = models.JSONField(null=True, blank=True)  # Updated
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Copay Log"
        verbose_name_plural = "Copay Logs"

    def __str__(self):
        return f"{self.transaction_name} | {self.get_status_display()} | {self.created_at}"