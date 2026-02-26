# # engine/tasks.py
# import asyncio
# import requests
# from urllib.parse import urlencode
# from celery import shared_task
# from django.conf import settings

# # --- Async corporate members ---
# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def sync_corp_members_task(self):
#     # Import locally to avoid AppRegistryNotReady
#     from engine.corpmembers import SyncHaisMembersAsyncView

#     service = SyncHaisMembersAsyncView()
#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#     return loop.run_until_complete(service.sync_all_members())


# # --- Async retail members ---
# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def sync_members_task(self):
#     from engine.retailmembers import SyncMembersServiceAsync

#     service = SyncMembersServiceAsync()
#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#     return loop.run_until_complete(service.sync_all_members_async())


# # --- Benefits sync ---
# @shared_task
# def sync_benefits_task():
#     # Import models inside function
#     from .models import BenefitSyncSuccess, BenefitSyncFailure

#     def get_hais_token():
#         payload = {
#             "name": "generateToken",
#             "param": {
#                 "consumer_key": settings.HAIS_API_CONSUMER_KEY,
#                 "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
#             }
#         }
#         resp = requests.post(
#             settings.HAIS_API_BASE_URL,
#             json=payload,
#             headers={"Content-Type": "application/json"}
#         )
#         return resp.json().get("response", {}).get("result", {}).get("accessToken")

#     def get_smart_token():
#         payload = {
#             "client_id": settings.SMART_CLIENT_ID,
#             "client_secret": settings.SMART_CLIENT_SECRET,
#             "grant_type": settings.SMART_GRANT_TYPE
#         }
#         resp = requests.post(
#             f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
#             headers={"Content-Type": "application/x-www-form-urlencoded"},
#             verify=False
#         )
#         return resp.json().get("access_token")

#     def get_hais_benefits(hais_token):
#         payload = {"name": "smartRetailBenefits", "param": {}}
#         resp = requests.post(
#             settings.HAIS_API_BASE_URL,
#             json=payload,
#             headers={
#                 "Authorization": f"Bearer {hais_token}",
#                 "Content-Type": "application/json"
#             }
#         )
#         return resp.json()

#     hais_token = get_hais_token()
#     if not hais_token:
#         print("Failed to get HAIS token")
#         return

#     smart_token = get_smart_token()
#     if not smart_token:
#         print("Failed to get SMART token")
#         return

#     benefits_resp = get_hais_benefits(hais_token)
#     if benefits_resp.get("response", {}).get("status") != 200:
#         print("Failed to fetch HAIS benefits:", benefits_resp)
#         return

#     benefits = benefits_resp["response"]["result"]
#     success, failed = 0, 0

#     for b in benefits:
#         family_no = b.get("category_id")
#         benefit_desc = b.get("benefit_name")
#         policy_number = b.get("scheme_id")
#         cln_ben_code = b.get("benefit_id")
#         anniv = b.get("anniv")
#         user_id = b.get("user_id")

#         payload = {
#             "benefitDesc": benefit_desc,
#             "policyNumber": policy_number,
#             "clnBenCode": cln_ben_code,
#             "userId": user_id,
#             "countrycode": settings.COUNTRY_CODE,
#             "customerid": settings.SMART_CUSTOMER_ID
#         }

#         smart_url = f"{settings.SMART_API_BASE_URL}benefits?{urlencode(payload)}"

#         try:
#             smart_resp = requests.post(
#                 smart_url,
#                 headers={"Authorization": f"Bearer {smart_token}"},
#                 verify=False
#             )
#             smart_data = smart_resp.json()
#             smart_httpcode = smart_resp.status_code
#         except Exception as e:
#             smart_data = {}
#             smart_httpcode = 500
#             print(f"Error pushing benefit {cln_ben_code}: {e}")

#         sync_status = 1 if smart_data.get("successful") else 3

#         benefit_summary = {
#             "benefit_id": cln_ben_code,
#             "benefit_name": benefit_desc,
#             "policy_no": policy_number,
#             "corp_id": policy_number,
#             "category": b.get("category_name"),
#             "anniv": anniv,
#             "smart_status": smart_httpcode,
#             "smart_response": smart_data
#         }

#         if sync_status == 1:
#             BenefitSyncSuccess.objects.create(**benefit_summary)
#             success += 1
#         else:
#             BenefitSyncFailure.objects.create(**benefit_summary)
#             failed += 1

#         print(f"Pushed benefit {cln_ben_code}, status: {sync_status}")

#     print(f"Sync complete: {success} succeeded, {failed} failed")
    
    
    
# # engine/tasks.py
# from celery import shared_task
# import requests
# from urllib.parse import urlencode
# from django.conf import settings

# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def sync_corp_members_task(self):
#     """
#     Fetch HAIS corporate members and push to SMART, logging success/failure in DB.
#     """
#     import asyncio
#     from .models import MemberSyncSuccess, MemberSyncFailure  # local import to avoid AppRegistryNotReady

#     class SyncHaisMembers:
#         """Move your existing API view logic here as methods"""

#         def get_hais_token(self):
#             payload = {
#                 "name": "generateToken",
#                 "param": {
#                     "consumer_key": settings.HAIS_API_CONSUMER_KEY,
#                     "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
#                 }
#             }
#             try:
#                 resp = requests.post(
#                     settings.HAIS_API_BASE_URL,
#                     json=payload,
#                     headers={"Content-Type": "application/json"},
#                     timeout=30
#                 )
#                 data = resp.json()
#                 if data.get("response", {}).get("status") == 200:
#                     return data["response"]["result"]["accessToken"]
#             except Exception:
#                 return None
#             return None

#         def get_smart_token(self):
#             payload = {
#                 "client_id": settings.SMART_CLIENT_ID,
#                 "client_secret": settings.SMART_CLIENT_SECRET,
#                 "grant_type": settings.SMART_GRANT_TYPE
#             }
#             try:
#                 resp = requests.post(
#                     f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
#                     headers={"Content-Type": "application/x-www-form-urlencoded"},
#                     verify=False,
#                     timeout=30
#                 )
#                 return resp.json().get("access_token")
#             except Exception:
#                 return None

#         def get_hais_members(self, hais_token):
#             payload = {"name": "smartCorporateMembers", "param": {}}
#             try:
#                 resp = requests.post(
#                     settings.HAIS_API_BASE_URL,
#                     json=payload,
#                     headers={
#                         "Authorization": f"Bearer {hais_token}",
#                         "Content-Type": "application/json"
#                     },
#                     timeout=60
#                 )
#                 return resp.json()
#             except Exception as e:
#                 return {"error": str(e)}

#         def update_hais_member(self, hais_token, member_no, anniv, status):
#             payload = {
#                 "name": "updateSmartMember",
#                 "param": {"member_no": member_no, "anniv": anniv, "status": status}
#             }
#             try:
#                 requests.post(
#                     settings.HAIS_API_BASE_URL,
#                     json=payload,
#                     headers={
#                         "Authorization": f"Bearer {hais_token}",
#                         "Content-Type": "application/json"
#                     },
#                     timeout=30
#                 )
#             except Exception:
#                 pass

#         def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
#             payload = {
#                 "name": "createApiLog",
#                 "param": {
#                     "source": "HAIS-SMART",
#                     "transactionName": "Corporate Scheme Member",
#                     "statusCode": smart_httpcode,
#                     "requestObject": [request_obj],
#                     "responseObject": [response_obj]
#                 }
#             }
#             try:
#                 requests.post(
#                     settings.HAIS_API_BASE_URL,
#                     json=payload,
#                     headers={
#                         "Authorization": f"Bearer {hais_token}",
#                         "Content-Type": "application/json"
#                     },
#                     timeout=30
#                 )
#             except Exception:
#                 pass

#         def push_members(self):
#             hais_token = self.get_hais_token()
#             if not hais_token:
#                 return {"error": "Failed to get HAIS token"}

#             smart_token = self.get_smart_token()
#             if not smart_token:
#                 return {"error": "Failed to get SMART token"}

#             members_resp = self.get_hais_members(hais_token)
#             if members_resp.get("response", {}).get("status") != 200:
#                 return {"error": "Failed to fetch members", "details": members_resp}

#             members = members_resp["response"]["result"]
#             success, failed = 0, 0

#             for m in members:
#                 try:
#                     names = m.get("member_name", "").split(" ")
#                     surname = names[0] if len(names) > 0 else ""
#                     second_name = names[1] if len(names) > 1 else ""
#                     third_name = names[2] if len(names) > 2 else ""
#                     other_names = "null"

#                     phone = m.get("mobile_no", "").replace(" ", "")
#                     mobile_phone = f"254{phone[-9:]}" if phone else ""
#                     dob = m.get("dob", "null")
#                     gender = m.get("gender", "")
#                     cln_cat_code = f"{m.get('category')}-{m.get('anniv')}"
#                     anniv = m.get("anniv")
#                     user_id = m.get("user_id")

#                     payload = {
#                         "familyCode": m.get("family_no"),
#                         "membershipNumber": m.get("member_no"),
#                         "staffNumber": m.get("member_no"),
#                         "surname": surname,
#                         "secondName": second_name,
#                         "thirdName": third_name,
#                         "otherNames": other_names,
#                         "idNumber": "",
#                         "dob": dob,
#                         "gender": gender,
#                         "nhifNumber": "",
#                         "memType": m.get("member_type"),
#                         "schemeStartDate": m.get("start_date"),
#                         "schemeEndDate": m.get("end_date"),
#                         "clnCatCode": cln_cat_code,
#                         "clnPolCode": m.get("corp_id"),
#                         "phone_number": mobile_phone,
#                         "email_address": m.get("email", ""),
#                         "userID": user_id,
#                         "country": settings.COUNTRY_CODE,
#                         "customerid": settings.SMART_CUSTOMER_ID,
#                         "roamingCountries": settings.COUNTRY_CODE
#                     }

#                     smart_url = f"{settings.SMART_API_BASE_URL}members?{urlencode(payload)}"
#                     smart_resp = requests.post(
#                         smart_url,
#                         headers={"Authorization": f"Bearer {smart_token}"},
#                         verify=False
#                     )
#                     smart_data = smart_resp.json()
#                     smart_httpcode = smart_resp.status_code

#                     sync_status = 1 if smart_data.get("successful") else 2

#                     self.update_hais_member(hais_token, m.get("member_no"), anniv, sync_status)
#                     self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

#                     member_summary = {
#                         "member_no": m.get("member_no"),
#                         "family_no": m.get("family_no"),
#                         "surname": surname,
#                         "second_name": second_name,
#                         "third_name": third_name,
#                         "other_names": other_names,
#                         "category": m.get("category"),
#                         "anniv": anniv,
#                         "corp_id": m.get("corp_id"),
#                         "smart_status": smart_httpcode,
#                         "smart_response": smart_data
#                     }

#                     if sync_status == 1:
#                         success += 1
#                         MemberSyncSuccess.objects.create(**member_summary)
#                     else:
#                         failed += 1
#                         MemberSyncFailure.objects.create(**member_summary)

#                 except Exception as e:
#                     failed += 1
#                     MemberSyncFailure.objects.create(
#                         member_no=m.get("member_no"),
#                         family_no=m.get("family_no"),
#                         surname=m.get("member_name", ""),
#                         second_name="",
#                         third_name="",
#                         other_names="null",
#                         category=m.get("category"),
#                         anniv=m.get("anniv"),
#                         corp_id=m.get("corp_id"),
#                         smart_status=500,
#                         smart_response={"error": str(e)}
#                     )

#             return {"success": success, "failed": failed, "total": len(members)}

#     # --- Run the sync ---
#     sync_service = SyncHaisMembers()
#     return sync_service.push_members()