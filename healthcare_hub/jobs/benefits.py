# engine/benefits/services.py
import requests
from urllib.parse import urlencode
from django.conf import settings

from engine.models import BenefitSyncFailure, BenefitSyncSuccess
# from .models import BenefitSyncSuccess, BenefitSyncFailure

class SyncHaisBenefitsService:
    """Service to sync HAIS benefits to SMART."""

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

    def run(self):
        """Run the sync process."""
        hais_token = self.get_hais_token()
        if not hais_token:
            print("Failed to get HAIS token")
            return

        smart_token = self.get_smart_token()
        if not smart_token:
            print("Failed to get SMART token")
            return

        benefits_resp = self.get_hais_benefits(hais_token)
        if benefits_resp.get("response", {}).get("status") != 200:
            print("Failed to fetch benefits:", benefits_resp)
            return

        benefits = benefits_resp["response"]["result"]
        success, failed = 0, 0

        for b in benefits:
            try:
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

                self.update_hais_benefit(hais_token, update_req)
                self.create_hais_log(hais_token, smart_httpcode, b, smart_data)

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

        print(f"HAIS benefits sync complete: {success} succeeded, {failed} failed")
        
        
    
        
# retail benefits

import time
from urllib.parse import urlencode
import requests
from django.conf import settings
from engine.models import BenefitSyncSuccess, BenefitSyncFailure  # Update import if needed

class SyncHaisRetailBenefitsService:
    """
    Service to sync HAIS retail benefits to SMART and log success/failure.
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

    def run(self):
        hais_token = self.get_hais_token()
        if not hais_token:
            print("Failed to get HAIS token")
            return

        smart_token = self.get_smart_token()
        if not smart_token:
            print("Failed to get SMART token")
            return

        benefits_resp = self.get_hais_benefits(hais_token)
        if benefits_resp.get("response", {}).get("status") != 200:
            print("Failed to fetch HAIS benefits")
            return

        benefits = benefits_resp["response"]["result"]
        print(f"Fetched {len(benefits)} HAIS retail benefits")

        success, failed = 0, 0
        max_per_minute = 200
        delay_per_request = 60 / max_per_minute  # ~0.3s per benefit

        for idx, b in enumerate(benefits, start=1):
            try:
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

                if sync_status == 1:
                    BenefitSyncSuccess.objects.create(**benefit_summary)
                    success += 1
                else:
                    BenefitSyncFailure.objects.create(**benefit_summary)
                    failed += 1

                print(f"Pushed benefit {idx}: {benefit_summary}")

                # Throttle per request
                if idx % max_per_minute == 0:
                    time.sleep(60)
                else:
                    time.sleep(delay_per_request)

            except Exception as e:
                failed += 1
                BenefitSyncFailure.objects.create(
                    corp_id=b.get("scheme_id"),
                    category=b.get("category_name"),
                    anniv=b.get("anniv"),
                    benefit_id=b.get("benefit_id"),
                    benefit_name=b.get("benefit_name"),
                    policy_no=b.get("scheme_id"),
                    smart_status=500,
                    smart_response={"error": str(e)}
                )

        print(f"Sync complete: {success} succeeded, {failed} failed")