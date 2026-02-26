import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import MemberRenewalSyncSuccess, MemberRenewalSyncFailure


class SyncMemberRenewalsView(APIView):
    """
    Sync Retail Member Renewals from HAIS to SMART
    Logs success and failure in database
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

    def get_hais_member_renewals(self, hais_token):
        payload = {"name": "smartRetailMemberRenewals", "param": {}}
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

    def update_hais_member_renewal_status(self, hais_token, membership_number, anniv, status):
        payload = {
            "name": "updateSmartMemberRenewal",
            "param": {
                "member_no": membership_number,
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
                "transactionName": "Retail Member Renewal",
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

        member_renewals_resp = self.get_hais_member_renewals(hais_token)
        if member_renewals_resp.get("response", {}).get("status") != 200:
            return Response(member_renewals_resp, status=400)

        renewals = member_renewals_resp["response"]["result"]
        success, failed = 0, 0

        for r in renewals:
            membership_number = r.get("member_no")
            anniv = r.get("anniv")
            start_date = r.get("start_date")
            end_date = r.get("end_date")
            user_id = r.get("user_id")

            payload = {
                "memberNumber": membership_number,
                "startDate": start_date,
                "endDate": end_date,
                "userId": user_id,
                "country": settings.COUNTRY_CODE,
                "customerid": settings.SMART_CUSTOMER_ID
            }

            smart_url = f"{settings.SMART_API_BASE_URL}members/renewals?{urlencode(payload)}"

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

            # Update HAIS status and create log
            self.update_hais_member_renewal_status(hais_token, membership_number, anniv, sync_status)
            self.create_hais_log(hais_token, smart_httpcode, r, smart_data)

            # Log success or failure in DB
            if sync_status == 1:
                success += 1
                MemberRenewalSyncSuccess.objects.create(
                    member_no=membership_number,
                    anniv=anniv,
                    start_date=start_date,
                    end_date=end_date,
                    user_id=user_id,
                    status_code=smart_httpcode,
                    smart_response=smart_data
                )
            else:
                failed += 1
                MemberRenewalSyncFailure.objects.create(
                    member_no=membership_number,
                    anniv=anniv,
                    start_date=start_date,
                    end_date=end_date,
                    user_id=user_id,
                    status_code=smart_httpcode,
                    smart_response=smart_data
                )

        return Response({
            "response": {
                "result": f"{success} member renewals synced successfully, {failed} failed"
            }
        })