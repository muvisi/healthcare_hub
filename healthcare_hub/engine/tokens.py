import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status



import requests
from urllib.parse import urlencode
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class GetSmartTokenView(APIView):
    """
    API to fetch SMART access token
    """

    def post(self, request):
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

            data = resp.json()

            token = data.get("access_token")

            if not token:
                return Response(
                    {"error": "Failed to get SMART token", "raw": data},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "access_token": token,
                    "token_type": data.get("token_type"),
                    "expires_in": data.get("expires_in"),
                    "raw_response": data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class HAISTokenView(APIView):
    """Return HAIS API token"""
    def get(self, request):
        try:
            response = requests.post(
                settings.HAIS_API_BASE_URL,
                json={
                    "name": "generateToken",
                    "param": {
                        "consumer_key": settings.HAIS_API_CONSUMER_KEY,
                        "consumer_secret": settings.HAIS_API_CONSUMER_SECRET
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            data = response.json()
            if data.get("response", {}).get("status") == 200:
                return Response({"access_token": data["response"]["result"]["accessToken"]})
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SMARTTokenView(APIView):
    """Return SMART API token"""
    def get(self, request):
        try:
            payload = {
                "client_id": settings.SMART_CLIENT_ID,
                "client_secret": settings.SMART_CLIENT_SECRET,
                "grant_type": settings.SMART_GRANT_TYPE
            }
            response = requests.post(
                f"{settings.SMART_ACCESS_TOKEN}{urlencode(payload)}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False
            )
            data = response.json()
            if "access_token" in data:
                return Response({"access_token": data["access_token"]})
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


