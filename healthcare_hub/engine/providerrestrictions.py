import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ProviderRestrictionSyncFailure, ProviderRestrictionSyncSuccess

class SyncProviderRestrictionsView(APIView):
    """
    Sync scheme provider restrictions from HAIS to SMART
    and log success & failures to the database.
    """

    def get_hais_token(self):
        payload = {
            "name": "generateToken",
            "param": {
                "consumer_key": settings.HAIS_API_CONSUMER_KEY,
                "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
            }
        }
        print("Requesting HAIS token...")
        resp = requests.post(
            settings.HAIS_API_BASE_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        data = resp.json()
        if data.get("response", {}).get("status") == 200:
            print("HAIS token retrieved successfully")
            return data["response"]["result"]["accessToken"]
        print("Failed to retrieve HAIS token:", data)
        return None

    def get_smart_token(self):
        payload = {
            "client_id": settings.SMART_CLIENT_ID,
            "client_secret": settings.SMART_CLIENT_SECRET,
            "grant_type": settings.SMART_GRANT_TYPE
        }
        print("Requesting SMART token...")
        resp = requests.post(
            f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            verify=False
        )
        data = resp.json()
        token = data.get("access_token")
        if token:
            print("SMART token retrieved successfully")
        else:
            print("Failed to retrieve SMART token", data)
        return token

    def get_hais_restrictions(self, hais_token):
        print("Fetching restrictions from HAIS...")
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
            "param": {"idx": rec_id, "status": status}
        }
        print(f"Updating HAIS restriction idx={rec_id} to status={status}...")
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
        print(f"Logging API call for corp_id={request_obj.get('corp_id')} to HAIS...")
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
        print("Starting provider restrictions sync...")

        hais_token = self.get_hais_token()
        if not hais_token:
            return Response({"error": "Failed to get HAIS token"}, status=400)

        smart_token = self.get_smart_token()
        if not smart_token:
            return Response({"error": "Failed to get SMART token"}, status=400)

        restrictions_resp = self.get_hais_restrictions(hais_token)
        if restrictions_resp.get("response", {}).get("status") != 200:
            print(f"Failed to get restrictions from HAIS: {restrictions_resp}")
            return Response(restrictions_resp, status=400)

        restrictions = restrictions_resp["response"]["result"]
        print(f"Fetched {len(restrictions)} restrictions from HAIS")

        success, failed = 0, 0

        for idx, r in enumerate(restrictions, start=1):
            print(f"\nProcessing restriction {idx}/{len(restrictions)}: {r.get('corp_id')} - {r.get('provider_code')}")
            payload = [{
                "integSchemeCode": r.get("corp_id"),
                "integProvCode": r.get("provider_code"),
                "integCatCodes": r.get("smart_restriction_category"),
                "lineUser": r.get("user_id"),
                "countryCode": settings.COUNTRY_CODE
            }]

            smart_url = f"{settings.SMART_API_BASE_URL}bulk/providers/restrictions?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"
            smart_resp = requests.post(
                smart_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {smart_token}",
                    "Content-Type": "application/json",
                    "customerid": settings.SMART_CUSTOMER_ID,
                    "country": settings.COUNTRY_CODE
                },
                verify=False
            )

            smart_data = smart_resp.json()
            smart_httpcode = smart_resp.status_code
            sync_status = 1 if smart_data.get("successful") else 2
            print(f"SMART response HTTP {smart_httpcode}, success={sync_status == 1}")

            self.update_hais_restriction_status(hais_token, r.get("idx"), sync_status)
            self.create_hais_log(hais_token, smart_httpcode, r, smart_data)

            # Log in database
            if sync_status == 1:
                success += 1
                ProviderRestrictionSyncSuccess.objects.create(
                    corp_id=r.get("corp_id"),
                    provider_code=r.get("provider_code"),
                    smart_restriction_category=r.get("smart_restriction_category"),
                    user_id=r.get("user_id"),
                    status_code=smart_httpcode,
                    smart_response=smart_data
                )
            else:
                failed += 1
                ProviderRestrictionSyncFailure.objects.create(
                    corp_id=r.get("corp_id"),
                    provider_code=r.get("provider_code"),
                    smart_restriction_category=r.get("smart_restriction_category"),
                    user_id=r.get("user_id"),
                    status_code=smart_httpcode,
                    smart_response=smart_data
                )

        print(f"\nSync complete: {success} success, {failed} failed")
        return Response({
            "response": {
                "result": f"{success} provider restriction(s) successfully synced, {failed} failed"
            }
        })