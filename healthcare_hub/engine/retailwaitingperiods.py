import json
from urllib.parse import urlencode
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import WaitingPeriodSyncFailure, WaitingPeriodSyncSuccess

class SyncWaitingPeriodsView(APIView):
    """
    Sync all Retail Scheme Waiting Periods from HAIS to SMART.
    Logs HAIS data, sends to SMART, and records successes and failures in DB.
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
            token = data["response"]["result"]["accessToken"]
            print("✅ HAIS ACCESS TOKEN:", token)
            return token
        print("❌ HAIS TOKEN ERROR:", data)
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
        token = data.get("access_token")
        print("SMART ACCESS TOKEN:", token)
        return token

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
        data = resp.json()
        print("TOTAL WAITING PERIODS FETCHED:", len(data.get("response", {}).get("result", [])))
        return data

    def update_hais_waiting_period_status(self, hais_token, family_no, anniv, benefit, status):
        payload = {
            "name": "updateRetailSchemeWaitingPeriod",
            "param": {
                "family_no": family_no,
                "anniv": anniv,
                "benefit": benefit,
                "status": status
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
        except Exception as e:
            print("❌ Failed to update HAIS status:", str(e))

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
        except Exception as e:
            print("❌ Failed to create HAIS log:", str(e))

    def post(self, request):
        hais_token = self.get_hais_token()
        if not hais_token:
            return Response({"error": "Failed to get HAIS token"}, status=400)

        smart_token = self.get_smart_token()
        if not smart_token:
            return Response({"error": "Failed to get SMART token"}, status=400)

        waiting_periods_resp = self.get_hais_waiting_periods(hais_token)
        if waiting_periods_resp.get("response", {}).get("status") != 200:
            print("❌ HAIS WAITING PERIODS ERROR:", waiting_periods_resp)
            return Response(waiting_periods_resp, status=400)

        periods = waiting_periods_resp["response"]["result"]
        success_count, failed_count = 0, 0

        for period in periods:
            try:
                scheme_code = period.get("scheme_id")
                family_no = period.get("family_no")
                category = period.get("category")
                benefit = period.get("benefit")
                anniv = period.get("anniv")
                waiting_days = int(period.get("waiting_period", 0))

                print("\n=== PROCESSING ===")
                print(json.dumps(period, indent=4))

                payload = {
                    "is_autogrowth": 0,
                    "autogrowth_max": 4,
                    "autogrowth_min": 2,
                    "autogrowth_rate": 1,
                    "autogrowth_rate_type": 2,
                    "autorep_limit": 0,
                    "autorep_limit_type": "2",
                    "has_reserve_parent": 0,
                    "integ_ben_code": benefit,
                    "integ_cat_code": category,
                    "integ_scheme_code": scheme_code,
                    "is_autogrowth2": 1,
                    "autogrowth2_json": "1=200000~2=400000~3=600000~4=700000~5=800000~6=800000~7=800000~8=800000~9=800000",
                    "is_autorep": 0,
                    "is_threshold": 0,
                    "is_waitingperiod": 1,
                    "reserve_action": 0,
                    "reserve_parent_pool": 0,
                    "threshold_action": 0,
                    "threshold_rate": 0,
                    "threshold_rate_type": 0,
                    "waiting_days": waiting_days,
                    "waiting_months": 0
                }

                smart_url = f"{settings.SMART_API_BASE_URL}benefit/rules?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"
                smart_resp = requests.post(
                    smart_url,
                    headers={
                        "Authorization": f"Bearer {smart_token}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    verify=False
                )
                smart_data = smart_resp.json()
                smart_httpcode = smart_resp.status_code

                print("SMART HTTP CODE:", smart_httpcode)
                print("SMART RESPONSE:", json.dumps(smart_data, indent=4))

                sync_status = 1 if smart_data.get("successful") else 2

                # update HAIS and create log
                self.update_hais_waiting_period_status(hais_token, family_no, anniv, benefit, sync_status)
                self.create_hais_log(hais_token, smart_httpcode, period, smart_data)

                # log both success and failure
                if sync_status == 1:
                    success_count += 1
                    WaitingPeriodSyncSuccess.objects.create(
                        scheme_id=scheme_code,
                        family_no=family_no,
                        benefit=benefit,
                        anniv=anniv,
                        status_code=smart_httpcode,
                        smart_response=smart_data
                    )
                else:
                    failed_count += 1
                    WaitingPeriodSyncFailure.objects.create(
                        scheme_id=scheme_code,
                        family_no=family_no,
                        benefit=benefit,
                        anniv=anniv,
                        status_code=smart_httpcode,
                        smart_response=smart_data
                    )

            except Exception as e:
                failed_count += 1
                print("❌ ERROR PROCESSING RECORD:", str(e))

        return Response({
            "response": {
                "result": f"{success_count} waiting period(s) successfully synced, {failed_count} failed"
            }
        })