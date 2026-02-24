import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncHaisMembersView(APIView):
    """
    Sync HAIS corporate members to SMART API
    """

    def get_hais_token(self):
        """Fetch HAIS access token"""
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
        """Fetch SMART access token"""
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
        """Fetch members from HAIS"""
        payload = {"name": "smartCorporateMembers", "param": {}}
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

    def update_hais_member(self, hais_token, member_no, anniv, status):
        """Update HAIS member sync status"""
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
        """Save API logs to HAIS"""
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
            # split member names
            names = m.get("member_name", "").split(" ")
            surname = names[0] if len(names) > 0 else ""
            second_name = names[1] if len(names) > 1 else ""
            third_name = names[2] if len(names) > 2 else ""
            other_names = "null"

            phone = m.get("mobile_no", "").replace(" ", "")
            mobile_phone = f"254{phone[-9:]}" if phone else ""

            dob = m.get("dob", "null")
            gender = m.get("gender", "")
            cln_cat_code = f"{m.get('category')}-{m.get('anniv')}"
            anniv = m.get("anniv")
            user_id = m.get("user_id")

            payload = {
                "familyCode": m.get("family_no"),
                "membershipNumber": m.get("member_no"),
                "staffNumber": m.get("member_no"),
                "surname": surname,
                "secondName": second_name,
                "thirdName": third_name,
                "otherNames": other_names,
                "idNumber": "",
                "dob": dob,
                "gender": gender,
                "nhifNumber": "",
                "memType": m.get("member_type"),
                "schemeStartDate": m.get("start_date"),
                "schemeEndDate": m.get("end_date"),
                "clnCatCode": cln_cat_code,
                "clnPolCode": m.get("corp_id"),
                "phone_number": mobile_phone,
                "email_address": m.get("email", ""),
                "userID": user_id,
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

            # update HAIS member status
            self.update_hais_member(hais_token, m.get("member_no"), anniv, sync_status)

            # create HAIS log
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


