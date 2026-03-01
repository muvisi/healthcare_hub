# # jobs/members.py
# import requests
# from urllib.parse import urlencode
# from django.conf import settings
# from engine.models import MemberSyncSuccess, MemberSyncFailure  # Use jobs models or import correctly

# class SyncHaisMembersService:
#     """Service to sync HAIS corporate members to SMART."""

#     def get_hais_token(self):
#         payload = {
#             "name": "generateToken",
#             "param": {
#                 "consumer_key": settings.HAIS_API_CONSUMER_KEY,
#                 "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
#             }
#         }
#         try:
#             resp = requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={"Content-Type": "application/json"},
#                 timeout=30
#             )
#             data = resp.json()
#             if data.get("response", {}).get("status") == 200:
#                 return data["response"]["result"]["accessToken"]
#         except Exception:
#             pass
#         return None

#     def get_smart_token(self):
#         payload = {
#             "client_id": settings.SMART_CLIENT_ID,
#             "client_secret": settings.SMART_CLIENT_SECRET,
#             "grant_type": settings.SMART_GRANT_TYPE
#         }
#         try:
#             resp = requests.post(
#                 f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
#                 headers={"Content-Type": "application/x-www-form-urlencoded"},
#                 verify=False,
#                 timeout=30
#             )
#             return resp.json().get("access_token")
#         except Exception:
#             return None

#     def get_hais_members(self, hais_token):
#         payload = {"name": "smartCorporateMembers", "param": {}}
#         try:
#             resp = requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {hais_token}",
#                     "Content-Type": "application/json"
#                 },
#                 timeout=60
#             )
#             return resp.json()
#         except Exception as e:
#             return {"error": str(e)}

#     def update_hais_member(self, hais_token, member_no, anniv, status):
#         payload = {
#             "name": "updateSmartMember",
#             "param": {"member_no": member_no, "anniv": anniv, "status": status}
#         }
#         try:
#             requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {hais_token}",
#                     "Content-Type": "application/json"
#                 },
#                 timeout=30
#             )
#         except Exception:
#             pass

#     def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
#         payload = {
#             "name": "createApiLog",
#             "param": {
#                 "source": "HAIS-SMART",
#                 "transactionName": "Corporate Scheme Member",
#                 "statusCode": smart_httpcode,
#                 "requestObject": [request_obj],
#                 "responseObject": [response_obj]
#             }
#         }
#         try:
#             requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {hais_token}",
#                     "Content-Type": "application/json"
#                 },
#                 timeout=30
#             )
#         except Exception:
#             pass

#     def run(self):
#         hais_token = self.get_hais_token()
#         if not hais_token:
#             print("Failed to get HAIS token")
#             return

#         smart_token = self.get_smart_token()
#         if not smart_token:
#             print("Failed to get SMART token")
#             return

#         members_resp = self.get_hais_members(hais_token)
#         if members_resp.get("response", {}).get("status") != 200:
#             print("Failed to fetch HAIS members", members_resp)
#             return

#         members = members_resp["response"]["result"]
#         success, failed = 0, 0

#         for m in members:
#             try:
#                 names = m.get("member_name", "").split(" ")
#                 surname = names[0] if len(names) > 0 else ""
#                 second_name = names[1] if len(names) > 1 else ""
#                 third_name = names[2] if len(names) > 2 else ""
#                 other_names = "null"

#                 phone = m.get("mobile_no", "").replace(" ", "")
#                 mobile_phone = f"254{phone[-9:]}" if phone else ""

#                 dob = m.get("dob", "null")
#                 gender = m.get("gender", "")
#                 anniv = m.get("anniv")
#                 user_id = m.get("user_id")
#                 cln_cat_code = f"{m.get('category')}-{anniv}"

#                 payload = {
#                     "familyCode": m.get("family_no"),
#                     "membershipNumber": m.get("member_no"),
#                     "staffNumber": m.get("member_no"),
#                     "surname": surname,
#                     "secondName": second_name,
#                     "thirdName": third_name,
#                     "otherNames": other_names,
#                     "idNumber": "",
#                     "dob": dob,
#                     "gender": gender,
#                     "nhifNumber": "",
#                     "memType": m.get("member_type"),
#                     "schemeStartDate": m.get("start_date"),
#                     "schemeEndDate": m.get("end_date"),
#                     "clnCatCode": cln_cat_code,
#                     "clnPolCode": m.get("corp_id"),
#                     "phone_number": mobile_phone,
#                     "email_address": m.get("email", ""),
#                     "userID": user_id,
#                     "country": settings.COUNTRY_CODE,
#                     "customerid": settings.SMART_CUSTOMER_ID,
#                     "roamingCountries": settings.COUNTRY_CODE
#                 }

#                 smart_url = f"{settings.SMART_API_BASE_URL}members?{urlencode(payload)}"
#                 smart_resp = requests.post(
#                     smart_url,
#                     headers={"Authorization": f"Bearer {smart_token}"},
#                     verify=False
#                 )
#                 smart_data = smart_resp.json()
#                 smart_httpcode = smart_resp.status_code

#                 sync_status = 1 if smart_data.get("successful") else 2

#                 self.update_hais_member(hais_token, m.get("member_no"), anniv, sync_status)
#                 self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

#                 member_summary = {
#                     "member_no": m.get("member_no"),
#                     "family_no": m.get("family_no"),
#                     "surname": surname,
#                     "second_name": second_name,
#                     "third_name": third_name,
#                     "other_names": other_names,
#                     "category": m.get("category"),
#                     "anniv": anniv,
#                     "corp_id": m.get("corp_id"),
#                     "smart_status": smart_httpcode,
#                     "smart_response": smart_data
#                 }

#                 if sync_status == 1:
#                     success += 1
#                     MemberSyncSuccess.objects.create(**member_summary)
#                 else:
#                     failed += 1
#                     MemberSyncFailure.objects.create(**member_summary)

#             except Exception as e:
#                 failed += 1
#                 MemberSyncFailure.objects.create(
#                     member_no=m.get("member_no"),
#                     family_no=m.get("family_no"),
#                     surname=m.get("member_name", ""),
#                     second_name="",
#                     third_name="",
#                     other_names="null",
#                     category=m.get("category"),
#                     anniv=m.get("anniv"),
#                     corp_id=m.get("corp_id"),
#                     smart_status=500,
#                     smart_response={"error": str(e)}
#                 )

#         print(f"Members sync complete: {success} succeeded, {failed} failed")
        



# class SyncRetailMembersService:
#     """
#     Sync retail members from HAIS to SMART (Job version of API)
#     """

#     def get_hais_token(self):
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
#             headers={"Content-Type": "application/json"},
#             timeout=30
#         )
#         data = resp.json()
#         if data.get("response", {}).get("status") == 200:
#             return data["response"]["result"]["accessToken"]
#         return None

#     def get_smart_token(self):
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
#         data = resp.json()
#         return data.get("access_token")

#     def get_hais_members(self, hais_token):
#         payload = {"name": "smartRetailMembers", "param": {}}
#         resp = requests.post(
#             settings.HAIS_API_BASE_URL,
#             json=payload,
#             headers={
#                 "Authorization": f"Bearer {hais_token}",
#                 "Content-Type": "application/json"
#             },
#             timeout=30
#         )
#         return resp.json()

#     def update_hais_member_status(self, hais_token, member_no, anniv, status):
#         payload = {
#             "name": "updateSmartMember",
#             "param": {
#                 "member_no": member_no,
#                 "anniv": anniv,
#                 "status": status
#             }
#         }
#         requests.post(
#             settings.HAIS_API_BASE_URL,
#             json=payload,
#             headers={
#                 "Authorization": f"Bearer {hais_token}",
#                 "Content-Type": "application/json"
#             },
#             timeout=30
#         )

#     def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
#         payload = {
#             "name": "createApiLog",
#             "param": {
#                 "source": "HAIS-SMART",
#                 "transactionName": "Retail Member",
#                 "statusCode": smart_httpcode,
#                 "requestObject": [request_obj],
#                 "responseObject": [response_obj]
#             }
#         }
#         requests.post(
#             settings.HAIS_API_BASE_URL,
#             json=payload,
#             headers={
#                 "Authorization": f"Bearer {hais_token}",
#                 "Content-Type": "application/json"
#             },
#             timeout=30
#         )

#     def run(self):
#         print("🔄 RETAIL MEMBERS SYNC JOB STARTED")

#         hais_token = self.get_hais_token()
#         if not hais_token:
#             print("❌ Failed to get HAIS token")
#             return

#         smart_token = self.get_smart_token()
#         if not smart_token:
#             print("❌ Failed to get SMART token")
#             return

#         members_resp = self.get_hais_members(hais_token)
#         if members_resp.get("response", {}).get("status") != 200:
#             print("❌ Failed to fetch HAIS members")
#             return

#         members = members_resp["response"]["result"]

#         success, failed = 0, 0

#         for m in members:
#             cln_pol_code = m.get("scheme_id")
#             membership_number = m.get("member_no")
#             family_code = m.get("family_no")
#             anniv = m.get("anniv")
#             cln_cat_code = f"{family_code}-{anniv}"
#             mem_type = m.get("memType")

#             member_names = m.get("member_name", "").split(" ")
#             surname = member_names[0] if len(member_names) > 0 else ""
#             second_name = member_names[1] if len(member_names) > 1 else ""
#             third_name = member_names[2] if len(member_names) > 2 else ""

#             dob = m.get("dob", "")
#             gender = m.get("gender", "")
#             scheme_start_date = m.get("start_date")
#             scheme_end_date = m.get("end_date")

#             phone_no = m.get("mobile_no", "").replace(" ", "")
#             mobile_phone = f"254{phone_no[-9:]}" if phone_no else ""
#             email = m.get("email", "")

#             user_id = m.get("user_id")
#             roaming_countries = "KE"

#             payload = {
#                 "familyCode": family_code,
#                 "membershipNumber": membership_number,
#                 "staffNumber": membership_number,
#                 "surname": surname,
#                 "secondName": second_name,
#                 "thirdName": third_name,
#                 "otherNames": "",
#                 "idNumber": "",
#                 "dob": dob,
#                 "gender": gender,
#                 "nhifNumber": "",
#                 "memType": mem_type,
#                 "schemeStartDate": scheme_start_date,
#                 "schemeEndDate": scheme_end_date,
#                 "clnCatCode": cln_cat_code,
#                 "clnPolCode": cln_pol_code,
#                 "phone_number": mobile_phone,
#                 "email_address": email,
#                 "userID": user_id,
#                 "country": settings.COUNTRY_CODE,
#                 "customerid": settings.SMART_CUSTOMER_ID,
#                 "roamingCountries": roaming_countries
#             }

#             smart_url = f"{settings.SMART_API_BASE_URL}members?{urlencode(payload)}"

#             try:
#                 smart_resp = requests.post(
#                     smart_url,
#                     headers={"Authorization": f"Bearer {smart_token}"},
#                     verify=False
#                 )
#                 smart_data = smart_resp.json()
#                 smart_httpcode = smart_resp.status_code
#             except Exception as e:
#                 print(f"❌ SMART request failed: {e}")
#                 smart_data = {}
#                 smart_httpcode = 500

#             sync_status = 1 if smart_data.get("successful") else 2

#             self.update_hais_member_status(hais_token, membership_number, anniv, sync_status)
#             self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

#             if sync_status == 1:
#                 success += 1
#             else:
#                 failed += 1

#         print(f"✅ RETAIL MEMBERS SYNC DONE → {success} success, {failed} failed")

# import requests
# from urllib.parse import urlencode
# from django.conf import settings
# from engine.models import MemberSyncSuccess, MemberSyncFailure
# from django.core.mail import EmailMessage
# from django.template.loader import render_to_string


# class SyncHaisMembersService:
#     """Service to sync HAIS corporate members to SMART and email summary."""

#     def get_hais_token(self):
#         payload = {
#             "name": "generateToken",
#             "param": {
#                 "consumer_key": settings.HAIS_API_CONSUMER_KEY,
#                 "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
#             }
#         }
#         try:
#             resp = requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={"Content-Type": "application/json"},
#                 timeout=30
#             )
#             data = resp.json()
#             if data.get("response", {}).get("status") == 200:
#                 return data["response"]["result"]["accessToken"]
#         except Exception:
#             pass
#         return None

#     def get_smart_token(self):
#         payload = {
#             "client_id": settings.SMART_CLIENT_ID,
#             "client_secret": settings.SMART_CLIENT_SECRET,
#             "grant_type": settings.SMART_GRANT_TYPE
#         }
#         try:
#             resp = requests.post(
#                 f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
#                 headers={"Content-Type": "application/x-www-form-urlencoded"},
#                 verify=False,
#                 timeout=30
#             )
#             return resp.json().get("access_token")
#         except Exception:
#             return None

#     def get_hais_members(self, hais_token):
#         payload = {"name": "smartCorporateMembers", "param": {}}
#         try:
#             resp = requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {hais_token}",
#                     "Content-Type": "application/json"
#                 },
#                 timeout=60
#             )
#             return resp.json()
#         except Exception as e:
#             return {"error": str(e)}

#     def update_hais_member(self, hais_token, member_no, anniv, status):
#         payload = {
#             "name": "updateSmartMember",
#             "param": {"member_no": member_no, "anniv": anniv, "status": status}
#         }
#         try:
#             requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {hais_token}",
#                     "Content-Type": "application/json"
#                 },
#                 timeout=30
#             )
#         except Exception:
#             pass

#     def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
#         payload = {
#             "name": "createApiLog",
#             "param": {
#                 "source": "HAIS-SMART",
#                 "transactionName": "Corporate Scheme Member",
#                 "statusCode": smart_httpcode,
#                 "requestObject": [request_obj],
#                 "responseObject": [response_obj]
#             }
#         }
#         try:
#             requests.post(
#                 settings.HAIS_API_BASE_URL,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {hais_token}",
#                     "Content-Type": "application/json"
#                 },
#                 timeout=30
#             )
#         except Exception:
#             pass

#     def send_email_summary(self, members_summary, success_count, failed_count):
#         """Send email with synced members summary."""
#         subject = f"[Madison Healthcare] HAIS Members Sync Report"
#         html_content = render_to_string("emails/members_summary.html", {
#             "members": members_summary,
#             "success_count": success_count,
#             "failed_count": failed_count,
#         })
#         email = EmailMessage(
#             subject,
#             html_content,
#             settings.EMAIL_HOST_USER,
#             ["mwangangimuvisi@gmail.com"],  # Test recipient
#         )
#         email.content_subtype = "html"
#         email.send(fail_silently=False)

#     def run(self):
#         hais_token = self.get_hais_token()
#         if not hais_token:
#             print("Failed to get HAIS token")
#             return

#         smart_token = self.get_smart_token()
#         if not smart_token:
#             print("Failed to get SMART token")
#             return

#         members_resp = self.get_hais_members(hais_token)
#         if members_resp.get("response", {}).get("status") != 200:
#             print("Failed to fetch HAIS members", members_resp)
#             return

#         members = members_resp["response"]["result"]
#         success, failed = 0, 0
#         members_summary = []

#         for m in members:
#             try:
#                 names = m.get("member_name", "").split(" ")
#                 surname = names[0] if len(names) > 0 else ""
#                 second_name = names[1] if len(names) > 1 else ""
#                 third_name = names[2] if len(names) > 2 else ""
#                 other_names = "null"

#                 phone = m.get("mobile_no", "").replace(" ", "")
#                 mobile_phone = f"254{phone[-9:]}" if phone else ""
#                 anniv = m.get("anniv")

#                 payload = {
#                     "familyCode": m.get("family_no"),
#                     "membershipNumber": m.get("member_no"),
#                     "staffNumber": m.get("member_no"),
#                     "surname": surname,
#                     "secondName": second_name,
#                     "thirdName": third_name,
#                     "otherNames": other_names,
#                     "idNumber": "",
#                     "dob": m.get("dob", "null"),
#                     "gender": m.get("gender", ""),
#                     "nhifNumber": "",
#                     "memType": m.get("member_type"),
#                     "schemeStartDate": m.get("start_date"),
#                     "schemeEndDate": m.get("end_date"),
#                     "clnCatCode": f"{m.get('category')}-{anniv}",
#                     "clnPolCode": m.get("corp_id"),
#                     "phone_number": mobile_phone,
#                     "email_address": m.get("email", ""),
#                     "userID": m.get("user_id"),
#                     "country": settings.COUNTRY_CODE,
#                     "customerid": settings.SMART_CUSTOMER_ID,
#                     "roamingCountries": settings.COUNTRY_CODE
#                 }

#                 smart_url = f"{settings.SMART_API_BASE_URL}members?{urlencode(payload)}"
#                 smart_resp = requests.post(
#                     smart_url,
#                     headers={"Authorization": f"Bearer {smart_token}"},
#                     verify=False
#                 )
#                 smart_data = smart_resp.json()
#                 smart_httpcode = smart_resp.status_code

#                 sync_status = 1 if smart_data.get("successful") else 2

#                 self.update_hais_member(hais_token, m.get("member_no"), anniv, sync_status)
#                 self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

#                 member_summary = {
#                     "member_no": m.get("member_no"),
#                     "family_no": m.get("family_no"),
#                     "surname": surname,
#                     "second_name": second_name,
#                     "third_name": third_name,
#                     "other_names": other_names,
#                     "category": m.get("category"),
#                     "anniv": anniv,
#                     "corp_id": m.get("corp_id"),
#                     "smart_status": smart_httpcode,
#                     "smart_response": smart_data
#                 }
#                 members_summary.append(member_summary)

#                 if sync_status == 1:
#                     success += 1
#                     MemberSyncSuccess.objects.create(**member_summary)
#                 else:
#                     failed += 1
#                     MemberSyncFailure.objects.create(**member_summary)

#             except Exception as e:
#                 failed += 1
#                 MemberSyncFailure.objects.create(
#                     member_no=m.get("member_no"),
#                     family_no=m.get("family_no"),
#                     surname=m.get("member_name", ""),
#                     second_name="",
#                     third_name="",
#                     other_names="null",
#                     category=m.get("category"),
#                     anniv=m.get("anniv"),
#                     corp_id=m.get("corp_id"),
#                     smart_status=500,
#                     smart_response={"error": str(e)}
#                 )

#         print(f"Members sync complete: {success} succeeded, {failed} failed")

#         # Send email after sync
#         self.send_email_summary(members_summary, success, failed)
#         print("✅ Summary email sent")


# jobs/members.py
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from engine.models import MemberSyncSuccess, MemberSyncFailure  # adjust import if needed


class SyncHaisMembersService:
    """Service to sync HAIS corporate members to SMART."""

    def get_hais_token(self):
        payload = {
            "name": "generateToken",
            "param": {
                "consumer_key": settings.HAIS_API_CONSUMER_KEY,
                "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
            }
        }
        try:
            resp = requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            data = resp.json()
            if data.get("response", {}).get("status") == 200:
                return data["response"]["result"]["accessToken"]
        except Exception:
            pass
        return None

    def get_smart_token(self):
        payload = {
            "client_id": settings.SMART_CLIENT_ID,
            "client_secret": settings.SMART_CLIENT_SECRET,
            "grant_type": settings.SMART_GRANT_TYPE
        }
        try:
            resp = requests.post(
                f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False,
                timeout=30
            )
            return resp.json().get("access_token")
        except Exception:
            return None

    def get_hais_members(self, hais_token):
        payload = {"name": "smartCorporateMembers", "param": {}}
        try:
            resp = requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {hais_token}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def update_hais_member(self, hais_token, member_no, anniv, status):
        payload = {
            "name": "updateSmartMember",
            "param": {"member_no": member_no, "anniv": anniv, "status": status}
        }
        try:
            requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {hais_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
        except Exception:
            pass

    def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
        payload = {
            "name": "createApiLog",
            "param": {
                "source": "HAIS-SMART",
                "transactionName": "Corporate Scheme Member",
                "statusCode": smart_httpcode,
                "requestObject": [request_obj],
                "responseObject": [response_obj]
            }
        }
        try:
            requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {hais_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
        except Exception:
            pass

    def send_email_summary(self, members_summary, success_count, failed_count):
        """Send email with synced members summary using same template."""
        subject = f"[Madison Healthcare] HAIS Members Sync Report"
        html_content = render_to_string("emails/members_summary.html", {
            "members": members_summary,
            "success_count": success_count,
            "failed_count": failed_count,
        })
        email = EmailMessage(
            subject,
            html_content,
            settings.EMAIL_HOST_USER,
            ["mwangangimuvisi@gmail.com"],  # Test recipient
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)

    def run(self):
        hais_token = self.get_hais_token()
        if not hais_token:
            print("Failed to get HAIS token")
            return

        smart_token = self.get_smart_token()
        if not smart_token:
            print("Failed to get SMART token")
            return

        members_resp = self.get_hais_members(hais_token)
        if members_resp.get("response", {}).get("status") != 200:
            print("Failed to fetch HAIS members", members_resp)
            return

        members = members_resp["response"]["result"]
        success, failed = 0, 0
        members_summary = []

        for m in members:
            try:
                names = m.get("member_name", "").split(" ")
                surname = names[0] if len(names) > 0 else ""
                second_name = names[1] if len(names) > 1 else ""
                third_name = names[2] if len(names) > 2 else ""
                other_names = "null"

                phone = m.get("mobile_no", "").replace(" ", "")
                mobile_phone = f"254{phone[-9:]}" if phone else ""
                anniv = m.get("anniv")

                payload = {
                    "familyCode": m.get("family_no"),
                    "membershipNumber": m.get("member_no"),
                    "staffNumber": m.get("member_no"),
                    "surname": surname,
                    "secondName": second_name,
                    "thirdName": third_name,
                    "otherNames": other_names,
                    "idNumber": "",
                    "dob": m.get("dob", "null"),
                    "gender": m.get("gender", ""),
                    "nhifNumber": "",
                    "memType": m.get("member_type"),
                    "schemeStartDate": m.get("start_date"),
                    "schemeEndDate": m.get("end_date"),
                    "clnCatCode": f"{m.get('category')}-{anniv}",
                    "clnPolCode": m.get("corp_id"),
                    "phone_number": mobile_phone,
                    "email_address": m.get("email", ""),
                    "userID": m.get("user_id"),
                    "country": settings.COUNTRY_CODE,
                    "customerid": settings.SMART_CUSTOMER_ID,
                    "roamingCountries": settings.COUNTRY_CODE
                }

                smart_url = f"{settings.SMART_API_BASE_URL}members?{urlencode(payload)}"
                smart_resp = requests.post(
                    smart_url,
                    headers={"Authorization": f"Bearer {smart_token}"},
                    verify=False
                )
                smart_data = smart_resp.json()
                smart_httpcode = smart_resp.status_code

                sync_status = 1 if smart_data.get("successful") else 2

                self.update_hais_member(hais_token, m.get("member_no"), anniv, sync_status)
                self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

                member_summary = {
                    "member_no": m.get("member_no"),
                    "family_no": m.get("family_no"),
                    "surname": surname,
                    "second_name": second_name,
                    "third_name": third_name,
                    "other_names": other_names,
                    "category": m.get("category"),
                    "anniv": anniv,
                    "corp_id": m.get("corp_id"),
                    "smart_status": smart_httpcode,
                    "smart_response": smart_data
                }
                members_summary.append(member_summary)

                if sync_status == 1:
                    success += 1
                    MemberSyncSuccess.objects.create(**member_summary)
                else:
                    failed += 1
                    MemberSyncFailure.objects.create(**member_summary)

            except Exception as e:
                failed += 1
                MemberSyncFailure.objects.create(
                    member_no=m.get("member_no"),
                    family_no=m.get("family_no"),
                    surname=m.get("member_name", ""),
                    second_name="",
                    third_name="",
                    other_names="null",
                    category=m.get("category"),
                    anniv=m.get("anniv"),
                    corp_id=m.get("corp_id"),
                    smart_status=500,
                    smart_response={"error": str(e)}
                )

        print(f"Members sync complete: {success} succeeded, {failed} failed")

        # Send email summary after processing all members
        self.send_email_summary(members_summary, success, failed)
        print("✅ Summary email sent")
        
        
        
        
# jobs/members.py
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from engine.models import MemberSyncSuccess, MemberSyncFailure  # adjust import if needed


class SyncRetailMembersService:
    """
    Sync retail members from HAIS to SMART (Job version of API)
    """

    def get_hais_token(self):
        payload = {
            "name": "generateToken",
            "param": {
                "consumer_key": settings.HAIS_API_CONSUMER_KEY,
                "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
            }
        }
        resp = requests.post(
            settings.HAIS_API_BASE_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        data = resp.json()
        if data.get("response", {}).get("status") == 200:
            return data["response"]["result"]["accessToken"]
        return None

    def get_smart_token(self):
        payload = {
            "client_id": settings.SMART_CLIENT_ID,
            "client_secret": settings.SMART_CLIENT_SECRET,
            "grant_type": settings.SMART_GRANT_TYPE
        }
        resp = requests.post(
            f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            verify=False
        )
        data = resp.json()
        return data.get("access_token")

    def get_hais_members(self, hais_token):
        payload = {"name": "smartRetailMembers", "param": {}}
        resp = requests.post(
            settings.HAIS_API_BASE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {hais_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        return resp.json()

    def update_hais_member_status(self, hais_token, member_no, anniv, status):
        payload = {
            "name": "updateSmartMember",
            "param": {
                "member_no": member_no,
                "anniv": anniv,
                "status": status
            }
        }
        requests.post(
            settings.HAIS_API_BASE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {hais_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

    def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
        payload = {
            "name": "createApiLog",
            "param": {
                "source": "HAIS-SMART",
                "transactionName": "Retail Member",
                "statusCode": smart_httpcode,
                "requestObject": [request_obj],
                "responseObject": [response_obj]
            }
        }
        requests.post(
            settings.HAIS_API_BASE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {hais_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

    def send_email_summary(self, members_summary, success_count, failed_count):
        """Send email with synced members summary using same template."""
        subject = f"[Madison Healthcare] HAIS Members Sync Report"
        html_content = render_to_string("emails/members_summary.html", {
            "members": members_summary,
            "success_count": success_count,
            "failed_count": failed_count,
        })
        email = EmailMessage(
            subject,
            html_content,
            settings.EMAIL_HOST_USER,
            ["mwangangimuvisi@gmail.com"],  # Test recipient
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)

    def run(self):
        print("🔄 RETAIL MEMBERS SYNC JOB STARTED")

        hais_token = self.get_hais_token()
        if not hais_token:
            print("❌ Failed to get HAIS token")
            return

        smart_token = self.get_smart_token()
        if not smart_token:
            print("❌ Failed to get SMART token")
            return

        members_resp = self.get_hais_members(hais_token)
        if members_resp.get("response", {}).get("status") != 200:
            print("❌ Failed to fetch HAIS members")
            return

        members = members_resp["response"]["result"]

        success, failed = 0, 0
        members_summary = []

        for m in members:
            cln_pol_code = m.get("scheme_id")
            membership_number = m.get("member_no")
            family_code = m.get("family_no")
            anniv = m.get("anniv")
            cln_cat_code = f"{family_code}-{anniv}"
            mem_type = m.get("memType")

            member_names = m.get("member_name", "").split(" ")
            surname = member_names[0] if len(member_names) > 0 else ""
            second_name = member_names[1] if len(member_names) > 1 else ""
            third_name = member_names[2] if len(member_names) > 2 else ""

            dob = m.get("dob", "")
            gender = m.get("gender", "")
            scheme_start_date = m.get("start_date")
            scheme_end_date = m.get("end_date")

            phone_no = m.get("mobile_no", "").replace(" ", "")
            mobile_phone = f"254{phone_no[-9:]}" if phone_no else ""
            email = m.get("email", "")

            user_id = m.get("user_id")
            roaming_countries = "KE"

            payload = {
                "familyCode": family_code,
                "membershipNumber": membership_number,
                "staffNumber": membership_number,
                "surname": surname,
                "secondName": second_name,
                "thirdName": third_name,
                "otherNames": "",
                "idNumber": "",
                "dob": dob,
                "gender": gender,
                "nhifNumber": "",
                "memType": mem_type,
                "schemeStartDate": scheme_start_date,
                "schemeEndDate": scheme_end_date,
                "clnCatCode": cln_cat_code,
                "clnPolCode": cln_pol_code,
                "phone_number": mobile_phone,
                "email_address": email,
                "userID": user_id,
                "country": settings.COUNTRY_CODE,
                "customerid": settings.SMART_CUSTOMER_ID,
                "roamingCountries": roaming_countries
            }

            smart_url = f"{settings.SMART_API_BASE_URL}members?{urlencode(payload)}"

            try:
                smart_resp = requests.post(
                    smart_url,
                    headers={"Authorization": f"Bearer {smart_token}"},
                    verify=False
                )
                smart_data = smart_resp.json()
                smart_httpcode = smart_resp.status_code
            except Exception as e:
                print(f"❌ SMART request failed: {e}")
                smart_data = {}
                smart_httpcode = 500

            sync_status = 1 if smart_data.get("successful") else 2

            self.update_hais_member_status(hais_token, membership_number, anniv, sync_status)
            self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

            member_summary = {
                "member_no": membership_number,
                "family_no": family_code,
                "surname": surname,
                "second_name": second_name,
                "third_name": third_name,
                "other_names": "",
                "category": mem_type,
                "anniv": anniv,
                "corp_id": cln_pol_code,
                "smart_status": smart_httpcode,
                "smart_response": smart_data
            }
            members_summary.append(member_summary)

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        print(f"✅ RETAIL MEMBERS SYNC DONE → {success} success, {failed} failed")

        # Send email summary after retail sync
        self.send_email_summary(members_summary, success, failed)
        print("✅ Summary email sent for retail members")