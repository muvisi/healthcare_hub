import json
from urllib.parse import urlencode
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BenefitSyncSuccess, BenefitSyncFailure


class SyncHaisBenefitsView(APIView):
    """
    Sync HAIS benefits to SMART, log success/failure in DB, and create HAIS logs.
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
        except Exception:
            pass
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
                timeout=30,
                verify=False
            )
            return resp.json().get("access_token")
        except Exception:
            return None

    def get_hais_benefits(self, hais_token):
        payload = {"name": "smartBenefits", "param": {}}
        try:
            resp = requests.post(
                settings.HAIS_API_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {hais_token}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def update_hais_benefit(self, hais_token, update_request):
        try:
            requests.post(
                settings.HAIS_API_BASE_URL,
                json=update_request,
                headers={
                    "Authorization": f"Bearer {hais_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
        except Exception:
            pass

    def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
        payload = {
            "name": "createApiLog",
            "param": {
                "source": "HAIS-SMART",
                "transactionName": "Corporate Scheme Benefit",
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
        except Exception:
            pass

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

        benefits = benefits_resp["response"]["result"]
        success, failed = 0, 0

        for b in benefits:
            try:
                # Build SMART payload
                benefit_desc = b.get("benefit_name")
                policy_no = b.get("policy_no")
                cln_pol_code = b.get("corp_id")
                cat_desc = b.get("category_name")
                cln_ben_code = b.get("benefit_id")
                anniv = b.get("anniv")
                user_id = b.get("user_id")
                ben_linked = b.get("sub_limit_of") if b.get("sub_limit_of") != "0" else "-"

                url_data = {
                    "benefitDesc": benefit_desc,
                    "policyNumber": policy_no,
                    "clnPolCode": cln_pol_code,
                    "catCode": f"{cat_desc}-{anniv}",
                    "clnBenCode": cln_ben_code,
                    "benLinked2Tqcode": ben_linked,
                    "userId": user_id,
                    "countrycode": settings.COUNTRY_CODE,
                    "customerid": settings.SMART_CUSTOMER_ID
                }

                smart_url = f"{settings.SMART_API_BASE_URL}benefits?{urlencode(url_data)}"
                smart_resp = requests.post(
                    smart_url,
                    headers={"Authorization": f"Bearer {smart_token}"},
                    timeout=60,
                    verify=False
                )

                try:
                    smart_data = smart_resp.json()
                except Exception:
                    smart_data = {"error": smart_resp.text}

                smart_httpcode = smart_resp.status_code
                sync_status = 1 if smart_data.get("successful") else 3

                update_req = {
                    "name": "updateSchemeBenefits",
                    "param": {
                        "corp_id": cln_pol_code,
                        "anniv": anniv,
                        "category": cat_desc,
                        "benefit": cln_ben_code,
                        "status": sync_status
                    }
                }

                # Update HAIS and create log
                self.update_hais_benefit(hais_token, update_req)
                self.create_hais_log(hais_token, smart_httpcode, b, smart_data)

                # Save to DB
                summary = {
                    "corp_id": cln_pol_code,
                    "category": cat_desc,
                    "anniv": anniv,
                    "benefit_id": cln_ben_code,
                    "benefit_name": benefit_desc,
                    "policy_no": policy_no,
                    "smart_status": smart_httpcode,
                    "smart_response": smart_data
                }

                if sync_status == 1:
                    success += 1
                    BenefitSyncSuccess.objects.create(**summary)
                else:
                    failed += 1
                    BenefitSyncFailure.objects.create(**summary)

            except Exception as e:
                failed += 1
                BenefitSyncFailure.objects.create(
                    corp_id=b.get("corp_id"),
                    category=b.get("category_name"),
                    anniv=b.get("anniv"),
                    benefit_id=b.get("benefit_id"),
                    benefit_name=b.get("benefit_name"),
                    policy_no=b.get("policy_no"),
                    smart_status=500,
                    smart_response={"error": str(e)}
                )

        return Response({
            "response": {
                "summary": f"{success} benefits successfully synced to SMART, {failed} failed",
                "total_fetched": len(benefits)
            }
        })