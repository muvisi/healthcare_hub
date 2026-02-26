import time
from urllib.parse import urlencode
import requests
from django.conf import settings
from engine.models import CopayLog  # Adjust this import path if needed

class SyncHaisCopaysService:
    """
    Service to sync HAIS corporate scheme copays to SMART
    and log all transactions in CopayLog.
    """

    def get_hais_token(self):
        payload = {
            "name": "generateToken",
            "param": {
                "consumer_key": settings.HAIS_API_CONSUMER_KEY,
                "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
            }
        }
        try:
            resp = requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            data = resp.json()
            if data.get("response", {}).get("status") == 200:
                return data["response"]["result"]["accessToken"]
        except Exception as e:
            CopayLog.objects.create(
                transaction_name="Get HAIS Token",
                status_code=0,
                request_object=payload,
                response_object={"error": str(e)},
                status=2
            )
        return None

    def get_smart_token(self):
        payload = {
            "client_id": settings.SMART_CLIENT_ID,
            "client_secret": settings.SMART_CLIENT_SECRET,
            "grant_type": settings.SMART_GRANT_TYPE
        }
        try:
            resp = requests.post(
                f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False,
                timeout=30
            )
            return resp.json().get("access_token")
        except Exception as e:
            CopayLog.objects.create(
                transaction_name="Get SMART Token",
                status_code=0,
                request_object=payload,
                response_object={"error": str(e)},
                status=2
            )
        return None

    def get_hais_copays(self, hais_token):
        payload = {"name": "smartCopays", "param": {}}
        try:
            resp = requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={"Authorization": f"Bearer {hais_token}", "Content-Type": "application/json"},
                timeout=30
            )
            return resp.json()
        except Exception as e:
            CopayLog.objects.create(
                transaction_name="Get HAIS Copays",
                status_code=0,
                request_object=payload,
                response_object={"error": str(e)},
                status=2
            )
            return {"response": {"status": 500, "result": None, "error": str(e)}}

    def update_hais_copay(self, hais_token, idx, status):
        payload = {"name": "updateCorpCopayStatus", "param": {"idx": idx, "status": status}}
        try:
            requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={"Authorization": f"Bearer {hais_token}", "Content-Type": "application/json"},
                timeout=30
            )
        except Exception as e:
            CopayLog.objects.create(
                transaction_name="Update HAIS Copay",
                status_code=0,
                request_object=payload,
                response_object={"error": str(e)},
                status=2
            )

    def create_api_log(self, status_code, request_obj, response_obj, status):
        CopayLog.objects.create(
            transaction_name="Corporate Scheme Copay",
            status_code=status_code,
            request_object=request_obj,
            response_object=response_obj,
            status=status
        )

    def run(self):
        """Main sync logic"""
        hais_token = self.get_hais_token()
        if not hais_token:
            print("❌ Failed to get HAIS token")
            return

        smart_token = self.get_smart_token()
        if not smart_token:
            self.create_api_log(
                status_code=0,
                request_obj={"action": "get_smart_token"},
                response_obj={"error": "Failed to get SMART token"},
                status=2
            )
            print("❌ Failed to get SMART token")
            return

        copays_resp = self.get_hais_copays(hais_token)
        if copays_resp.get("response", {}).get("status") != 200:
            self.create_api_log(
                status_code=copays_resp.get("response", {}).get("status", 0),
                request_obj={"action": "get_hais_copays"},
                response_obj=copays_resp,
                status=2
            )
            print("❌ Failed to fetch HAIS copays")
            return

        copays = copays_resp["response"]["result"]
        print(f"Fetched {len(copays)} copays from HAIS")

        success, failed = 0, 0

        for idx, c in enumerate(copays, start=1):
            payload = {
                "integ_scheme_code": c.get("corp_id"),
                "integ_cat_code": c.get("smart_copay_category"),
                "integ_ben_code": c.get("benefit_code"),
                "integ_prov_code": c.get("provider_code"),
                "integ_service_code": c.get("service_code"),
                "copay_type": int(c.get("copay_type", 0)),
                "amount": float(c.get("copay_amt", 0.0))
            }

            smart_url = f"{settings.SMART_API_BASE_URL}copay/setup?{urlencode({'country': settings.COUNTRY_CODE, 'customerid': settings.SMART_CUSTOMER_ID})}"

            try:
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
                    timeout=30
                )
                smart_data = smart_resp.json()
                smart_httpcode = smart_resp.status_code
                sync_status = 1 if smart_data.get("successful") else 2
            except Exception as e:
                smart_data = {"error": str(e)}
                smart_httpcode = 0
                sync_status = 2

            # Update HAIS copay status
            self.update_hais_copay(hais_token, c.get("idx"), sync_status)

            # Log transaction
            self.create_api_log(
                status_code=smart_httpcode,
                request_obj=payload,
                response_obj=smart_data,
                status=sync_status
            )

            if sync_status == 1:
                success += 1
            else:
                failed += 1

        print(f"✅ Sync complete: {success} succeeded, {failed} failed")