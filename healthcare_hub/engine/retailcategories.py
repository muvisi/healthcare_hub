import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response


class SyncRetailCategoriesView(APIView):
    """
    Sync retail categories from HAIS to SMART
    """

    def get_hais_token(self):
        payload = {"name": "generateToken", "param": {
            "consumer_key": settings.HAIS_API_CONSUMER_KEY,
            "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
        }}
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
            verify=False
        )
        data = resp.json()
        return data.get("access_token")

    def get_hais_categories(self, hais_token):
        payload = {"name": "smartRetailCategories", "param": {}}
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

    def update_hais_category_status(self, hais_token, family_no, anniv, status):
        payload = {
            "name": "updateRetailSchemeCategory",
            "param": {
                "family_no": family_no,
                "anniv": anniv,
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
                "transactionName": "Retail Category",
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

        categories_resp = self.get_hais_categories(hais_token)
        if categories_resp.get("response", {}).get("status") != 200:
            return Response(categories_resp, status=400)

        categories = categories_resp["response"]["result"]
        success, failed = 0, 0

        for c in categories:
            family_no = c.get("category_id")
            anniv = c.get("anniv")
            cat_desc = f"{c.get('category_name')}-{anniv}"
            cln_cat_code = cat_desc
            cln_pol_code = c.get("scheme_id")
            user_id = c.get("user_id")

            payload = {
                "catDesc": cat_desc,
                "clnPolCode": cln_pol_code,
                "userId": user_id,
                "clnCatCode": cln_cat_code,
                "country": settings.COUNTRY_CODE,
                "customerid": settings.SMART_CUSTOMER_ID
            }

            smart_url = f"{settings.SMART_API_BASE_URL}benefitCategories?{urlencode(payload)}"
            smart_resp = requests.post(
                smart_url,
                headers={
                    "Authorization": f"Bearer {smart_token}",
                    "Content-Type": "application/json"
                },
                verify=False
            )
            smart_data = smart_resp.json()
            smart_httpcode = smart_resp.status_code

            sync_status = 2 if smart_data.get("successful") else 4

            self.update_hais_category_status(hais_token, family_no, anniv, sync_status)
            self.create_hais_log(hais_token, smart_httpcode, c, smart_data)

            if sync_status == 2:
                success += 1
            else:
                failed += 1

        return Response({
            "response": {
                "result": f"{success} retail categories successfully synced to SMART, {failed} failed"
            }
        })


