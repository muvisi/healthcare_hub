"""
Test script for Smart Schemes API integration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_hub.settings')
django.setup()

from smart.models import Corporate
from smart.schemes import push_scheme_to_smart_api
from datetime import date

# Create a test corporate record
test_corporate = Corporate(
    clnCode="TEST001",
    companyName="TEST COMPANY LTD",
    clnPolCode="TEST/SCHEME/001/2025",
    anniv=1,
    userId="test.user",
    polTypeId="1",
    startDate=date(2025, 1, 1),
    endDate=date(2026, 1, 1),
    countryCode="KE",
    synced=False
)

print("=" * 60)
print("Testing Smart Schemes API Integration")
print("=" * 60)

print("\n1. Test Corporate Data:")
print(f"   Company Name: {test_corporate.companyName}")
print(f"   Policy Code: {test_corporate.clnPolCode}")
print(f"   Start Date: {test_corporate.startDate}")
print(f"   End Date: {test_corporate.endDate}")
print(f"   Anniversary: {test_corporate.anniv}")

print("\n2. Testing API Push...")
result = push_scheme_to_smart_api(test_corporate)

print("\n3. API Response:")
print(f"   Success: {result.get('success')}")
if result.get('success'):
    print(f"   Message: {result.get('message')}")
    print(f"   Response: {result.get('response')}")
else:
    print(f"   Error: {result.get('error')}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
