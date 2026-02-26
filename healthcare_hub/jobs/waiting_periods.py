import json
import time
from urllib.parse import urlencode
import requests
from django.conf import settings
from engine.models import WaitingPeriodSyncSuccess, WaitingPeriodSyncFailure


class SyncHaisRetailWaitingPeriodsService:
    """
    Service to sync HAIS retail waiting periods to SMART and log success/failure.
    Uses same structure and throttling approach as benefits service.
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
            verify=False,
            timeout=30
        )
        return resp.json().get("access_token")

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

    def run(self):
        hais_token = self.get_hais_token()
        if not hais_token:
            print("Failed to get HAIS token")
            return

        smart_token = self.get_smart_token()
        if not smart_token:
            print("Failed to get SMART token")
            return

        waiting_resp = self.get_hais_waiting_periods(hais_token)
        if waiting_resp.get("response", {}).get("status") != 200:
            print("Failed to fetch HAIS waiting periods")
            return

        periods = waiting_resp["response"]["result"]
        print(f"Fetched {len(periods)} HAIS waiting periods")

        success, failed = 0, 0
        max_per_minute = 200
        delay_per_request = 60 / max_per_minute  # ~0.3s per record

        for idx, p in enumerate(periods, start=1):
            try:
                scheme_code = p.get("scheme_id")
                family_no = p.get("family_no")
                category = p.get("category")
                benefit = p.get("benefit")
                anniv = p.get("anniv")
                waiting_days = int(p.get("waiting_period", 0))

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

                try:
                    smart_resp = requests.post(
                        smart_url,
                        headers={
                            "Authorization": f"Bearer {smart_token}",
                            "Content-Type": "application/json"
                        },
                        json=payload,
                        verify=False,
                        timeout=30
                    )
                    smart_data = smart_resp.json()
                    smart_httpcode = smart_resp.status_code
                except Exception:
                    smart_data = {}
                    smart_httpcode = 500

                sync_status = 1 if smart_data.get("successful") else 3

                # Update HAIS + Log
                self.update_hais_waiting_period_status(hais_token, family_no, anniv, benefit, sync_status)
                self.create_hais_log(hais_token, smart_httpcode, p, smart_data)

                summary = {
                    "scheme_id": scheme_code,
                    "family_no": family_no,
                    "benefit": benefit,
                    "anniv": anniv,
                    "status_code": smart_httpcode,
                    "smart_response": smart_data
                }

                if sync_status == 1:
                    WaitingPeriodSyncSuccess.objects.create(**summary)
                    success += 1
                else:
                    WaitingPeriodSyncFailure.objects.create(**summary)
                    failed += 1

                print(f"Pushed waiting period {idx}: {summary}")

                # Throttle
                if idx % max_per_minute == 0:
                    time.sleep(60)
                else:
                    time.sleep(delay_per_request)

            except Exception as e:
                failed += 1
                WaitingPeriodSyncFailure.objects.create(
                    scheme_id=p.get("scheme_id"),
                    family_no=p.get("family_no"),
                    benefit=p.get("benefit"),
                    anniv=p.get("anniv"),
                    status_code=500,
                    smart_response={"error": str(e)}
                )

        print(f"Sync complete: {success} succeeded, {failed} failed")