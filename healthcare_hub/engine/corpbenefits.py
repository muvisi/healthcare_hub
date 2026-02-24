import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncHaisBenefitsView(APIView):
    """
    API to sync HAIS benefits to SMART and log transactions
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
        pushed_benefits = []
        failed_benefits = []

        for b in benefits:
            try:
                benefit_desc = b.get("benefit_name")
                policy_no = b.get("policy_no")
                ben_type_id = b.get("benefit_sharing")
                sub_limit = b.get("limit")
                service_type = b.get("benefit_class")
                mem_assigned = b.get("member_assigned_benefit")
                cln_pol_code = b.get("corp_id")
                cat_desc = b.get("category_name")
                cat_code = f"{cat_desc}-{b.get('anniv')}"
                cln_ben_code = b.get("benefit_id")
                ben_typ_desc = b.get("benefit_sharing_descr")
                anniv = b.get("anniv")
                user_id = b.get("user_id")
                ben_linked = b.get("sub_limit_of") if b.get("sub_limit_of") != "0" else "-"

                url_data = {
                    "benefitDesc": benefit_desc,
                    "policyNumber": policy_no,
                    "benTypeId": ben_type_id,
                    "subLimitAmt": sub_limit,
                    "serviceType": service_type,
                    "memAssignedBenefit": mem_assigned,
                    "clnPolCode": cln_pol_code,
                    "catCode": cat_code,
                    "clnBenCode": cln_ben_code,
                    "benTypDesc": ben_typ_desc,
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

                benefit_summary = {
                    "benefit_id": cln_ben_code,
                    "benefit_name": benefit_desc,
                    "policy_no": policy_no,
                    "corp_id": cln_pol_code,
                    "category": cat_desc,
                    "anniv": anniv,
                    "smart_status": smart_httpcode,
                    "smart_response": smart_data
                }

                if sync_status == 1:
                    success += 1
                    pushed_benefits.append(benefit_summary)
                else:
                    failed += 1
                    failed_benefits.append(benefit_summary)

            except Exception as e:
                failed += 1
                failed_benefits.append({
                    "benefit_id": b.get("benefit_id"),
                    "error": str(e)
                })

        return Response({
            "response": {
                "summary": f"{success} benefits successfully synced to SMART, {failed} failed",
                "total_fetched": len(benefits),
                "pushed_benefits": pushed_benefits,
                "failed_benefits": failed_benefits
            }
        })



# import requests
# from urllib.parse import urlencode
# from django.conf import settings
# from rest_framework.views import APIView
# from rest_framework.response import Response


# class SyncHaisBenefitsView(APIView):
#     """
#     API to sync HAIS benefits to SMART and log transactions
#     """

#     def get_hais_token(self):
#         """Fetch HAIS access token"""
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
#         """Fetch SMART access token"""
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

#     def get_hais_benefits(self, hais_token):
#         """Fetch benefits from HAIS"""
#         payload = {"name": "smartBenefits", "param": {}}
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

#     def update_hais_benefit(self, hais_token, update_request):
#         """Update HAIS benefit with sync status"""
#         resp = requests.post(
#             settings.HAIS_API_BASE_URL,
#             json=update_request,
#             headers={
#                 "Authorization": f"Bearer {hais_token}",
#                 "Content-Type": "application/json"
#             },
#             timeout=30
#         )
#         return resp.json()

#     def create_hais_log(self, hais_token, smart_httpcode, request_obj, response_obj):
#         """Save API logs to HAIS"""
#         payload = {
#             "name": "createApiLog",
#             "param": {
#                 "source": "HAIS-SMART",
#                 "transactionName": "Corporate Scheme Benefit",
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

#         benefits_resp = self.get_hais_benefits(hais_token)
#         if benefits_resp.get("response", {}).get("status") != 200:
#             return Response(benefits_resp, status=400)

#         benefits = benefits_resp["response"]["result"]
#         success, failed = 0, 0

#         for b in benefits:
#             benefit_desc = b.get("benefit_name")
#             policy_no = b.get("policy_no")
#             ben_type_id = b.get("benefit_sharing")
#             sub_limit = b.get("limit")
#             service_type = b.get("benefit_class")
#             mem_assigned = b.get("member_assigned_benefit")
#             cln_pol_code = b.get("corp_id")
#             cat_desc = b.get("category_name")
#             cat_code = f"{cat_desc}-{b.get('anniv')}"
#             cln_ben_code = b.get("benefit_id")
#             ben_typ_desc = b.get("benefit_sharing_descr")
#             anniv = b.get("anniv")
#             user_id = b.get("user_id")
#             ben_linked = b.get("sub_limit_of") if b.get("sub_limit_of") != "0" else "-"

#             url_data = {
#                 "benefitDesc": benefit_desc,
#                 "policyNumber": policy_no,
#                 "benTypeId": ben_type_id,
#                 "subLimitAmt": sub_limit,
#                 "serviceType": service_type,
#                 "memAssignedBenefit": mem_assigned,
#                 "clnPolCode": cln_pol_code,
#                 "catCode": cat_code,
#                 "clnBenCode": cln_ben_code,
#                 "benTypDesc": ben_typ_desc,
#                 "benLinked2Tqcode": ben_linked,
#                 "userId": user_id,
#                 "countrycode": settings.COUNTRY_CODE,
#                 "customerid": settings.SMART_CUSTOMER_ID
#             }

#             smart_url = f"{settings.SMART_API_BASE_URL}benefits?{urlencode(url_data)}"
#             smart_resp = requests.post(
#                 smart_url,
#                 headers={"Authorization": f"Bearer {smart_token}"},
#                 verify=False
#             )
#             smart_data = smart_resp.json()
#             smart_httpcode = smart_resp.status_code

#             sync_status = 1 if smart_data.get("successful") else 3

#             update_req = {
#                 "name": "updateSchemeBenefits",
#                 "param": {
#                     "corp_id": cln_pol_code,
#                     "anniv": anniv,
#                     "category": cat_desc,
#                     "benefit": cln_ben_code,
#                     "status": sync_status
#                 }
#             }

#             # Update HAIS and create log
#             self.update_hais_benefit(hais_token, update_req)
#             self.create_hais_log(hais_token, smart_httpcode, b, smart_data)

#             if sync_status == 1:
#                 success += 1
#             else:
#                 failed += 1

#         return Response({
#             "response": {
#                 "result": f"{success} benefits successfully synced to SMART, {failed} failed"
#             }
#         })


