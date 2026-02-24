import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json

class SyncHaisToSmartView(APIView):
    """
    API to sync HAIS schemes to SMART and update logs
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

    def get_hais_schemes(self, hais_token):
        payload = {"name": "smartSchemes", "param": {}}
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

    def update_hais_scheme(self, hais_token, update_request):
        resp = requests.post(
            settings.HAIS_API_BASE_URL,
            json=update_request,
            headers={
                "Authorization": f"Bearer {hais_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        return resp.json()

    def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
        payload = {
            "name": "createApiLog",
            "param": {
                "source": "HAIS-SMART",
                "transactionName": "Corporate Scheme",
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

        schemes_resp = self.get_hais_schemes(hais_token)
        if schemes_resp.get("response", {}).get("status") != 200:
            return Response(schemes_resp, status=400)

        schemes = schemes_resp["response"]["result"]
        success, failed = 0, 0

        for s in schemes:
            # Prepare SMART URL
            url_data = {
                "companyName": s.get("scheme_name"),
                "clnPolCode": s.get("corp_id"),
                "startDate": s.get("start_date"),
                "endDate": s.get("end_date"),
                "polTypeId": s.get("scheme_type_id"),
                "userId": s.get("user_id"),
                "anniv": s.get("anniv"),
                "policyCurrencyId": settings.POLICY_CURRENCY_ID,
                "countryCode": settings.COUNTRY_CODE,
                "customerid": settings.SMART_CUSTOMER_ID
            }
            smart_url = f"{settings.SMART_API_BASE_URL}schemes?{urlencode(url_data)}"

            # Send to SMART
            smart_resp = requests.post(
                smart_url,
                headers={"Authorization": f"Bearer {smart_token}"},
                verify=False
            )
            smart_data = smart_resp.json()
            smart_httpcode = smart_resp.status_code

            # Determine sync status
            sync_status = 1 if str(smart_data.get("successful")) == "true" else 2

            # Update HAIS accordingly
            if s.get("scheme_type") == "CORPORATE":
                update_req = {
                    "name": "updateCorporateScheme",
                    "param": {
                        "corp_id": s.get("corp_id"),
                        "anniv": s.get("anniv"),
                        "status": sync_status
                    }
                }
            else:
                update_req = {
                    "name": "updateRetailScheme",
                    "param": {
                        "corp_id": s.get("corp_id"),
                        "status": sync_status
                    }
                }
            self.update_hais_scheme(hais_token, update_req)

            # Create HAIS log
            self.create_hais_log(hais_token, smart_httpcode, s, smart_data)

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        return Response({
            "response": {
                "result": f"{success} scheme(s) successfully synced to SMART, {failed} failed"
            }
        })


