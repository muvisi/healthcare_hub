import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncRenewedSchemesView(APIView):
    """
    Sync renewed corporate schemes from HAIS to SMART API
    """

    def get_hais_token(self):
        payload = {"name": "generateToken", "param": {
            "consumer_key": settings.HAIS_API_CONSUMER_KEY,
            "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
        }}
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

    def get_hais_renewed_schemes(self, hais_token):
        payload = {"name": "smartRenewedSchemes", "param": {}}
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

    def update_hais_scheme_status(self, hais_token, corp_id, anniv, status):
        payload = {
            "name": "updateCorporateScheme",
            "param": {
                "corp_id": corp_id,
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
                "transactionName": "Corporate Scheme Renewal",
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

        schemes_resp = self.get_hais_renewed_schemes(hais_token)
        if schemes_resp.get("response", {}).get("status") != 200:
            return Response(schemes_resp, status=400)

        schemes = schemes_resp["response"]["result"]
        success, failed = 0, 0

        for s in schemes:
            payload = {
                "clnPolCode": s.get("corp_id"),
                "startDate": s.get("start_date"),
                "endDate": s.get("end_date"),
                "userId": s.get("user_id"),
                "country": settings.COUNTRY_CODE,
                "customerid": settings.SMART_CUSTOMER_ID
            }

            smart_url = f"{settings.SMART_API_BASE_URL}schemes/renewals?{urlencode(payload)}"
            smart_resp = requests.post(
                smart_url,
                headers={"Authorization": f"Bearer {smart_token}"},
                verify=False
            )
            smart_data = smart_resp.json()
            smart_httpcode = smart_resp.status_code

            sync_status = 1 if smart_data.get("successful") else 2

            # update HAIS scheme status
            self.update_hais_scheme_status(
                hais_token,
                s.get("corp_id"),
                s.get("anniv"),
                sync_status
            )

            # log API
            self.create_hais_log(hais_token, smart_httpcode, s, smart_data)

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        return Response({
            "response": {
                "result": f"{success} renewed scheme(s) successfully synced to SMART, {failed} failed"
            }
        })



