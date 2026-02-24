import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncHaisWaitingPeriodsView(APIView):
    """
    Sync HAIS Retail Scheme Waiting Periods to SMART API
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

    def get_hais_waiting_periods(self, hais_token):
        payload = {"name": "smartRetailWaitingPeriods", "param": {}}
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

    def update_hais_waiting_period(self, hais_token, family_no, anniv, benefit, status):
        payload = {
            "name": "updateRetailSchemeWaitingPeriod",
            "param": {
                "family_no": family_no,
                "anniv": anniv,
                "benefit": benefit,
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
                "transactionName": "Retail Scheme Waiting Period",
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

        waiting_resp = self.get_hais_waiting_periods(hais_token)
        if waiting_resp.get("response", {}).get("status") != 200:
            return Response(waiting_resp, status=400)

        periods = waiting_resp["response"]["result"]
        success, failed = 0, 0

        for p in periods:
            payload = {
                "integ_scheme_code": int(p.get("scheme_id")),
                "integ_cat_code": p.get("category"),
                "integ_ben_code": p.get("benefit"),
                "is_autogrowth": 0,
                "is_autogrowth2": 0,
                "is_waitingperiod": 1,
                "waiting_days": int(p.get("waiting_period", 0))
            }

            smart_url = f"{settings.SMART_API_BASE_URL}benefit/rules?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"
            smart_resp = requests.post(
                smart_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {smart_token}",
                    "Content-Type": "application/json"
                },
                verify=False
            )
            smart_data = smart_resp.json()
            smart_httpcode = smart_resp.status_code

            sync_status = 1 if smart_data.get("successful") else 2

            # update HAIS waiting period
            self.update_hais_waiting_period(
                hais_token,
                p.get("family_no"),
                p.get("anniv"),
                p.get("benefit"),
                sync_status
            )
            # create HAIS log
            self.create_hais_log(hais_token, smart_httpcode, p, smart_data)

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        return Response({
            "response": {
                "result": f"{success} waiting period(s) successfully synced to SMART, {failed} failed"
            }
        })


