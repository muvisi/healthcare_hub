from django.db import models

# Create your models here.
# smart/models.py
from django.db import models

class Corporate(models.Model):
    clnCode = models.CharField(max_length=50)
    companyName = models.CharField(max_length=255)
    clnPolCode = models.CharField(max_length=50, null=True, blank=True)
    anniv = models.IntegerField(null=True, blank=True)
    invoicePt = models.CharField(max_length=255, null=True, blank=True)
    invContactEmail = models.CharField(max_length=255, null=True, blank=True)
    invPtcontactTel = models.CharField(max_length=50, null=True, blank=True)
    polTypeId = models.CharField(max_length=50, null=True, blank=True)
    userId = models.CharField(max_length=50, null=True, blank=True)
    clnPolType = models.CharField(max_length=50, null=True, blank=True)
    policyNumber = models.CharField(max_length=50, null=True, blank=True)
    startDate = models.DateField(null=True, blank=True)
    endDate = models.DateField(null=True, blank=True)
    statusReason = models.CharField(max_length=50, default="NULL")
    cancelled = models.BooleanField(null=True, blank=True)
    countryCode = models.CharField(max_length=5, default="KE")
    created_at = models.DateTimeField(auto_now_add=True)
    synced = models.BooleanField(default=False)  # to track if pushed to Smart API

    def __str__(self):
        return f"{self.companyName} ({self.clnCode})"


from django.db import models

class BenefitCategory(models.Model):
    idx = models.IntegerField(default=0)
    catDesc = models.CharField(max_length=255)  # Category description
    userId = models.CharField(max_length=100)   # API user sending the request
    clnCatCode = models.CharField(max_length=50)  # Category code
    clnPolCode = models.CharField(max_length=50)  # Policy code
    customerid = models.CharField(max_length=50)  # Customer ID
    country = models.CharField(max_length=10)     # Country code
    created_at = models.DateTimeField(auto_now_add=True)  # Record creation timestamp
    updated_at = models.DateTimeField(auto_now=True)  
    synced = models.BooleanField(default=False)  # to track if pushed to Smart API

    class Meta:
        db_table = "benefit_category_payload"
        verbose_name = "Benefit Category Payload"
        verbose_name_plural = "Benefit Category Payloads"

    def __str__(self):
        return f"{self.clnCatCode} - {self.catDesc}"



class Benefit(models.Model):
    idx=models.IntegerField(default=0)
    clnPolCode = models.CharField(max_length=50)      # policy_no
    CatCode = models.CharField(max_length=50)         # category
    benTypeId = models.CharField(max_length=50, null=True, blank=True)  
    subLimitAmt = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    serviceType = models.CharField(max_length=50)    
    clnBenCode = models.CharField(max_length=50)      
    benefitDesc = models.CharField(max_length=255, null=True, blank=True)
    benLinked2Tqcode = models.CharField(max_length=50, null=True, blank=True)
    memAssignedBenefit = models.CharField(max_length=100, null=True, blank=True)
    Countrycode = models.CharField(max_length=5, default="KE")
    customerid = models.CharField(max_length=100, default="xyz")
    userId = models.CharField(max_length=100, default="msamuel")
    synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.clnBenCode} - {self.benefitDesc}"
