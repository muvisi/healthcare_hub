# import requests
# from urllib.parse import urlencode
# from django.conf import settings
# from rest_framework.views import APIView
# from rest_framework.response import Response


# class SyncProviderRestrictionsView(APIView):
#     """
#     Sync scheme provider restrictions from HAIS to SMART
#     """

#     def get_hais_token(self):
#         payload = {"name": "generateToken", "param": {
#             "consumer_key": settings.HAIS_API_CONSUMER_KEY,
#             "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
#         }}
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

#     def get_hais_restrictions(self, hais_token):
#         payload = {"name": "smartProviderRestrictions", "param": {}}
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

#     def update_hais_restriction_status(self, hais_token, rec_id, status):
#         payload = {
#             "name": "updateCorpProvRestrictionStatus",
#             "param": {
#                 "idx": rec_id,
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
#                 "transactionName": "Scheme Provider Restriction",
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

#         restrictions_resp = self.get_hais_restrictions(hais_token)
#         if restrictions_resp.get("response", {}).get("status") != 200:
#             return Response(restrictions_resp, status=400)

#         restrictions = restrictions_resp["response"]["result"]
#         success, failed = 0, 0

#         for r in restrictions:
#             payload = [{
#                 "integSchemeCode": r.get("corp_id"),
#                 "integProvCode": r.get("provider_code"),
#                 "integCatCodes": r.get("smart_restriction_category"),
#                 "lineUser": r.get("user_id"),
#                 "countryCode": settings.COUNTRY_CODE
#             }]

#             smart_url = f"{settings.SMART_API_BASE_URL}restrictions?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"
#             smart_resp = requests.post(
#                 smart_url,
#                 json=payload,
#                 headers={
#                     "Authorization": f"Bearer {smart_token}",
#                     "Content-Type": "application/json",
#                     "customerid": settings.SMART_CUSTOMER_ID,
#                     "country": settings.COUNTRY_CODE
#                 },
#                 verify=False
#             )
#             smart_data = smart_resp.json()
#             smart_httpcode = smart_resp.status_code

#             sync_status = 1 if smart_data.get("successful") else 2

#             self.update_hais_restriction_status(hais_token, r.get("idx"), sync_status)
#             self.create_hais_log(hais_token, smart_httpcode, r, smart_data)

#             if sync_status == 1:
#                 success += 1
#             else:
#                 failed += 1

#         return Response({
#             "response": {
#                 "result": f"{success} provider restriction(s) successfully synced to SMART, {failed} failed"
#             }
#         })

import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncProviderRestrictionsView(APIView):
    """
    Sync scheme provider restrictions from HAIS to SMART
    Stops on first SMART error and logs to terminal
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
            verify=False,
            timeout=30
        )

        print("SMART TOKEN HTTP CODE:", resp.status_code)
        print("SMART TOKEN RAW RESPONSE:", resp.text)

        data = resp.json()
        token = data.get("access_token")

        if token:
            print("SMART ACCESS TOKEN:", token)
        else:
            print("❌ SMART TOKEN ERROR:", data)

        return token

    def get_hais_restrictions(self, hais_token):
        payload = {"name": "smartProviderRestrictions", "param": {}}

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

    def update_hais_restriction_status(self, hais_token, rec_id, status):
        payload = {
            "name": "updateCorpProvRestrictionStatus",
            "param": {
                "idx": rec_id,
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
                "transactionName": "Scheme Provider Restriction",
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

        restrictions_resp = self.get_hais_restrictions(hais_token)

        if restrictions_resp.get("response", {}).get("status") != 200:
            print("❌ HAIS RESTRICTIONS ERROR:", restrictions_resp)
            return Response(restrictions_resp, status=400)

        restrictions = restrictions_resp["response"]["result"]

        print("TOTAL RESTRICTIONS FROM HAIS:", len(restrictions))

        success = 0
        failed = 0

        for r in restrictions:
            print("\nProcessing restriction IDX:", r.get("idx"))
            print("Restriction Data:", r)

            # Validate category before sending
            if not r.get("smart_restriction_category"):
                print("❌ SKIPPING - NO CATEGORY CODE")
                failed += 1
                break

            payload = [{
                "integSchemeCode": r.get("corp_id"),
                "integProvCode": r.get("provider_code"),
                "integCatCodes": r.get("smart_restriction_category"),
                "lineUser": str(r.get("user_id")) if r.get("user_id") is not None else "",
                "countryCode": settings.COUNTRY_CODE
            }]

            smart_url = (
                f"{settings.SMART_API_BASE_URL}bulk/providers/restrictions?"
                f"{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"
            )

            try:
                print("==== SENDING TO SMART ====")
                print("URL:", smart_url)
                print("Payload:", payload)

                smart_resp = requests.post(
                    smart_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {smart_token}",
                        "Content-Type": "application/json",
                        "customerid": settings.SMART_CUSTOMER_ID,
                        "country": settings.COUNTRY_CODE
                    },
                    verify=False,
                    timeout=60
                )

                smart_httpcode = smart_resp.status_code
                print("SMART HTTP CODE:", smart_httpcode)
                print("SMART RAW RESPONSE:", smart_resp.text)

                try:
                    smart_data = smart_resp.json()
                except Exception as json_err:
                    print("❌ JSON PARSE ERROR:", str(json_err))
                    smart_data = {"error": "Invalid JSON", "raw": smart_resp.text}

            except requests.exceptions.RequestException as req_err:
                print("❌ SMART REQUEST FAILED:", str(req_err))
                smart_httpcode = 500
                smart_data = {"error": str(req_err)}

            # Determine sync status
            if smart_data.get("successful"):
                sync_status = 1
                success += 1
            else:
                sync_status = 2
                failed += 1

                print("❌ FIRST SMART ERROR ENCOUNTERED — BREAKING LOOP")

                # Log to HAIS before breaking
                self.update_hais_restriction_status(
                    hais_token, r.get("idx"), sync_status
                )
                self.create_hais_log(
                    hais_token, smart_httpcode, r, smart_data
                )

                break  # 🔴 STOP ON FIRST ERROR

            # Update HAIS for successful record
            self.update_hais_restriction_status(
                hais_token, r.get("idx"), sync_status
            )
            self.create_hais_log(
                hais_token, smart_httpcode, r, smart_data
            )

        return Response({
            "response": {
                "result": f"{success} provider restriction(s) successfully synced to SMART, {failed} failed (stopped on first error)"
            }
        })