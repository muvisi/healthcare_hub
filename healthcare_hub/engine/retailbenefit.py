

import json
import time
from urllib.parse import urlencode
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BenefitSyncSuccess, BenefitSyncFailure  # Your Django models


class SyncBenefitsView(APIView):
    """
    Sync updated benefits from HAIS to SMART and log success/failure.
    Pushes 200 benefits per minute with overall timeout ~1.3 minutes for 200 benefits.
    Prints HAIS data to the terminal.
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
        data = resp.json()
        return data.get("access_token")

    def get_hais_benefits(self, hais_token):
        payload = {"name": "smartRetailBenefits", "param": {}}
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

    def update_hais_benefit_status(self, hais_token, family_no, anniv, cln_ben_code, status):
        payload = {
            "name": "updateRetailSchemeBenefits",
            "param": {
                "family_no": family_no,
                "anniv": anniv,
                "benefit": cln_ben_code,
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
                "transactionName": "Retail Scheme Benefit",
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

        benefits_resp = self.get_hais_benefits(hais_token)
        if benefits_resp.get("response", {}).get("status") != 200:
            return Response(benefits_resp, status=400)

        # Print all HAIS benefits data to terminal
        print("Fetched HAIS benefits data:")
        print(json.dumps(benefits_resp["response"]["result"], indent=2))

        benefits = benefits_resp["response"]["result"]
        success, failed = 0, 0
        pushed_benefits, failed_benefits = [], []

        # Rate limit: 200 benefits per minute
        max_per_minute = 200
        delay_per_request = 60 / max_per_minute  # ~0.3s per benefit

        for idx, b in enumerate(benefits, start=1):
            # --- prepare payload ---
            family_no = b.get("category_id")
            benefit_desc = b.get("benefit_name")
            policy_number = b.get("scheme_id")
            ben_type_id = b.get("benefit_sharing")
            sub_limit_amt = b.get("limit")
            service_type = b.get("service_type")
            mem_assigned_benefit = b.get("member_assigned_benefit")
            cln_pol_code = b.get("scheme_id")
            cat_code = f"{b.get('category_name')}-{b.get('anniv')}"
            cln_ben_code = b.get("benefit_id")
            ben_typ_desc = b.get("benefit_sharing_descr")
            anniv = b.get("anniv")
            user_id = b.get("user_id")
            ben_linked2tqcode = b.get("sub_limit_of") if b.get("sub_limit_of") != "0" else "-"

            payload = {
                "benefitDesc": benefit_desc,
                "policyNumber": policy_number,
                "benTypeId": ben_type_id,
                "subLimitAmt": sub_limit_amt,
                "serviceType": service_type,
                "memAssignedBenefit": mem_assigned_benefit,
                "clnPolCode": cln_pol_code,
                "catCode": cat_code,
                "clnBenCode": cln_ben_code,
                "benTypDesc": ben_typ_desc,
                "benLinked2Tqcode": ben_linked2tqcode,
                "userId": user_id,
                "countrycode": settings.COUNTRY_CODE,
                "customerid": settings.SMART_CUSTOMER_ID
            }

            smart_url = f"{settings.SMART_API_BASE_URL}benefits?{urlencode(payload)}"
            try:
                smart_resp = requests.post(
                    smart_url,
                    headers={"Authorization": f"Bearer {smart_token}"},
                    verify=False,
                    timeout=30
                )
                smart_data = smart_resp.json()
                smart_httpcode = smart_resp.status_code
            except Exception:
                smart_data = {}
                smart_httpcode = 500

            sync_status = 1 if smart_data.get("successful") else 3

            # Update HAIS and create log
            self.update_hais_benefit_status(hais_token, family_no, anniv, cln_ben_code, sync_status)
            self.create_hais_log(hais_token, smart_httpcode, b, smart_data)

            benefit_summary = {
                "benefit_id": cln_ben_code,
                "benefit_name": benefit_desc,
                "policy_no": policy_number,
                "corp_id": cln_pol_code,
                "category": b.get("category_name"),
                "anniv": anniv,
                "smart_status": smart_httpcode,
                "smart_response": smart_data
            }

            # Log to Django models
            if sync_status == 1:
                BenefitSyncSuccess.objects.create(**benefit_summary)
                pushed_benefits.append(benefit_summary)
                success += 1
            else:
                BenefitSyncFailure.objects.create(**benefit_summary)
                failed_benefits.append(benefit_summary)
                failed += 1

            # Print each benefit being pushed (optional)
            print(f"Pushing benefit {idx}: {json.dumps(benefit_summary)}")

            # Throttle: small delay per request
            if idx % max_per_minute == 0:
                time.sleep(60)  # pause 60s every 200 benefits
            else:
                time.sleep(delay_per_request)

        return Response({
            "response": {
                "summary": f"{success} benefits successfully synced, {failed} failed",
                "total_fetched": len(benefits),
                "pushed_benefits": pushed_benefits,
                "failed_benefits": failed_benefits
            }
        })
        
        
    