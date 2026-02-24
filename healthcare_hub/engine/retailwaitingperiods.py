# import json
# from urllib.parse import urlencode
# import requests
# from django.conf import settings
# from rest_framework.views import APIView
# from rest_framework.response import Response


# class SyncWaitingPeriodsView(APIView):
#     """
#     Sync Retail Scheme Waiting Periods from HAIS to SMART
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

#     def get_hais_waiting_periods(self, hais_token):
#         payload = {"name": "smartRetailWaitingPeriods", "param": {}}
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

#     def update_hais_waiting_period_status(self, hais_token, family_no, anniv, benefit, status):
#         payload = {
#             "name": "updateRetailSchemeWaitingPeriod",
#             "param": {
#                 "family_no": family_no,
#                 "anniv": anniv,
#                 "benefit": benefit,
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
#                 "transactionName": "Retail Scheme Waiting Period",
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

#     def post(self, request):
#         hais_token = self.get_hais_token()
#         if not hais_token:
#             return Response({"error": "Failed to get HAIS token"}, status=400)

#         smart_token = self.get_smart_token()
#         if not smart_token:
#             return Response({"error": "Failed to get SMART token"}, status=400)

#         waiting_periods_resp = self.get_hais_waiting_periods(hais_token)
#         if waiting_periods_resp.get("response", {}).get("status") != 200:
#             return Response(waiting_periods_resp, status=400)

#         periods = waiting_periods_resp["response"]["result"]
#         success, failed = 0, 0

#         for period in periods:
#             scheme_code = period.get("scheme_id")
#             family_no = period.get("family_no")
#             category = period.get("category")
#             benefit = period.get("benefit")
#             anniv = period.get("anniv")
#             waiting_days = int(period.get("waiting_period", 0))

#             logs_data = period

#             payload = {
#                 "is_autogrowth": 0,
#                 "integ_ben_code": benefit,
#                 "integ_cat_code": category,
#                 "integ_scheme_code": scheme_code,
#                 "is_autogrowth2": 0,
#                 "is_waitingperiod": 1,
#                 "waiting_days": waiting_days
#             }

#             smart_url = f"{settings.SMART_API_BASE_URL}benefit/rules?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"

#             try:
#                 smart_resp = requests.post(
#                     smart_url,
#                     headers={"Authorization": f"Bearer {smart_token}", "Content-Type": "application/json"},
#                     json=payload,
#                     verify=False
#                 )
#                 smart_data = smart_resp.json()
#                 smart_httpcode = smart_resp.status_code
#             except Exception:
#                 smart_data = {}
#                 smart_httpcode = 500

#             sync_status = 1 if smart_data.get("successful") else 2

#             # update HAIS status and create log
#             self.update_hais_waiting_period_status(hais_token, family_no, anniv, benefit, sync_status)
#             self.create_hais_log(hais_token, smart_httpcode, period, smart_data)

#             if sync_status == 1:
#                 success += 1
#             else:
#                 failed += 1

#         return Response({
#             "response": {
#                 "result": f"{success} waiting period(s) successfully synced to SMART, {failed} failed"
#             }
#         })


import json
from urllib.parse import urlencode
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncWaitingPeriodsView(APIView):
    """
    Sync Retail Scheme Waiting Periods from HAIS to SMART
    Logs HAIS data before posting to SMART
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
            print("HAIS ACCESS TOKEN:", token)
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
        print("SMART TOKEN RAW RESPONSE:", data)
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
        print("TOTAL WAITING PERIODS FETCHED FROM HAIS:", len(periods))

        success, failed = 0, 0

        for period in periods:
            scheme_code = period.get("scheme_id")
            family_no = period.get("family_no")
            category = period.get("category")
            benefit = period.get("benefit")
            anniv = period.get("anniv")
            waiting_days = int(period.get("waiting_period", 0))

            # 🔹 LOG THE DATA FROM HAIS BEFORE SENDING TO SMART
            print("\n=== HAIS DATA READY FOR SMART POST ===")
            print(json.dumps(period, indent=4))
            payload = {
                    "is_autogrowth": 0,
                    "autogrowth_min": 0,
                    "autogrowth_max": 0,
                    "autogrowth_rate": 0,
                    "autogrowth_rate_type": 0,
                    "autorep_limit": 0,
                    "autorep_limit_type": "0",
                    "has_reserve_parent": 0,
                    "reserve_action": 0,
                    "reserve_parent_pool": 0,
                    "threshold_action": 0,
                    "threshold_rate": 0,
                    "threshold_rate_type": 0,
                    "integ_ben_code": benefit,          # from your HAIS data
                    "integ_cat_code": category,         # from your HAIS data
                    "integ_scheme_code": scheme_code,   # from your HAIS data
                    "is_autogrowth2": 0,
                    "autogrowth2_json": "",
                    "is_waitingperiod": 1,
                    "waiting_days": waiting_days,       # from your HAIS data
                    "waiting_months": 0
                }

            # payload = {
            #     "is_autogrowth": 0,
            #     "integ_ben_code": benefit,
            #     "integ_cat_code": category,
            #     "integ_scheme_code": scheme_code,
            #     "is_autogrowth2": 0,
            #     "is_waitingperiod": 1,
            #     "waiting_days": waiting_days
            # }

            smart_url = f"{settings.SMART_API_BASE_URL}benefit/rules?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"

            try:
                print("==== SENDING TO SMART ====")
                print("SMART PAYLOAD:", json.dumps(payload, indent=4))

                smart_resp = requests.post(
                    smart_url,
                    headers={"Authorization": f"Bearer {smart_token}", "Content-Type": "application/json"},
                    json=payload,
                    verify=False
                )
                smart_data = smart_resp.json()
                smart_httpcode = smart_resp.status_code
                print("SMART HTTP CODE:", smart_httpcode)
                print("SMART RAW RESPONSE:", json.dumps(smart_data, indent=4))
            except Exception as e:
                print("❌ SMART REQUEST FAILED:", str(e))
                smart_data = {}
                smart_httpcode = 500

            sync_status = 1 if smart_data.get("successful") else 2

            # update HAIS status and create log
            self.update_hais_waiting_period_status(hais_token, family_no, anniv, benefit, sync_status)
            self.create_hais_log(hais_token, smart_httpcode, period, smart_data)

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        return Response({
            "response": {
                "result": f"{success} waiting period(s) successfully synced to SMART, {failed} failed"
            }
        })
