import json
from urllib.parse import urlencode
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncMembersView(APIView):
    """
    Sync retail members from HAIS to SMART
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

    def post(self, request):
        hais_token = self.get_hais_token()
        if not hais_token:
            return Response({"error": "Failed to get HAIS token"}, status=400)

        smart_token = self.get_smart_token()
        if not smart_token:
            return Response({"error": "Failed to get SMART token"}, status=400)

        members_resp = self.get_hais_members(hais_token)
        if members_resp.get("response", {}).get("status") != 200:
            return Response(members_resp, status=400)

        members = members_resp["response"]["result"]
        success, failed = 0, 0

        for m in members:
            # extract member details
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
            other_names = ""

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
                "otherNames": other_names,
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
            except Exception:
                smart_data = {}
                smart_httpcode = 500

            sync_status = 1 if smart_data.get("successful") else 2

            # update HAIS and create log
            self.update_hais_member_status(hais_token, membership_number, anniv, sync_status)
            self.create_hais_log(hais_token, smart_httpcode, m, smart_data)

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        return Response({
            "response": {
                "result": f"{success} member(s) successfully synced to SMART, {failed} failed"
            }
        })

