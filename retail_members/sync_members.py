


import logging
from datetime import datetime
from typing import Optional, List, Dict
import requests
from django.conf import settings

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(filename="smart_sync.log", level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


def fetch_smart_token() -> Optional[str]:
    """
    Fetch OAuth token from Smart API.
    Returns access_token if successful, otherwise None.
    """
    url = (
        f"{settings.SMART_TOKEN_URL}"
        f"?grant_type={settings.SMART_GRANT_TYPE}"
        f"&client_id={settings.SMART_CLIENT_ID}"
        f"&client_secret={settings.SMART_CLIENT_SECRET}"
    )
    print(f"Fetching Smart token from URL: {url}")

    try:
        response = requests.post(url, headers={}, data={}, timeout=10, verify=False)
        print(f"[Smart Token] HTTP {response.status_code}: {response.text}")
        logger.info(f"[Smart Token] HTTP {response.status_code}: {response.text}")

        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")

        if not token:
            print(f"[Smart Token] Failed to get token: {data}")
            logger.error(f"[Smart Token] Failed to get token: {data}")
        return token

    except requests.RequestException as e:
        print(f"[Smart Token] Exception: {e}")
        logger.exception(f"[Smart Token] Exception while fetching token: {e}")
        return None


def fetch_hais_members() -> List[Dict]:
    """
    Fetch members from HAIS API and log response.
    """
    params = {
        "consumer_key": settings.HAIS_CONSUMER_KEY,
        "consumer_secret": settings.HAIS_CONSUMER_SECRET
    }
    try:
        response = requests.post(settings.HAIS_API_BASE_URL, params=params, headers={"Content-Length": "0"}, timeout=15)
        response.raise_for_status()
        data = response.json()
        result = data.get("response", {}).get("result", [])
        print(f"[HAIS] Fetched {len(result)} members")
        logger.info(f"[HAIS] Fetched {len(result)} members")
        return result
    except requests.RequestException as e:
        print(f"[HAIS] Exception fetching members: {e}")
        logger.exception(f"[HAIS] Exception fetching members: {e}")
        return []


def post_member_to_smart(member: Dict, token: str) -> bool:
    """
    Post a single member to Smart API, log responses.
    """
    def fix_null(val):
        return val if val is not None else "NULL"

    payload = {
        "familyCode": member.get("familyCode"),
        "membershipNumber": member.get("membershipNumber"),
        "staffNumber": member.get("staffNumber"),
        "idNumber": fix_null(member.get("idNumber")),
        "nhifNumber": "NULL",
        "surname": fix_null(member.get("Surname")),
        "secondName": fix_null(member.get("secondName")),
        "thirdName": fix_null(member.get("otherName")),
        "otherNames": "NULL",
        "dob": member.get("Dob"),
        "userID": member.get("userId"),
        "gender": member.get("gender"),
        "memType": member.get("memType"),
        "schemeStartDate": member.get("schemeStartDate"),
        "schemeEndDate": member.get("schemeEndDate"),
        "clnCatCode": f"{member.get('medCatg', '')}{member.get('prodCode', '')}-{member.get('ann')}",
        "clnPolCode": member.get("clnPolCode"),
        "country": settings.COUNTRY_CODE,
        "customerid": settings.SMART_CUSTOMER_ID,
        "roamingCountries": settings.COUNTRY_CODE,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(settings.SMART_API_URL, params=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"[Smart API] Member {member.get('membershipNumber')} response: {data}")
        logger.info(f"[Smart API] Member {member.get('membershipNumber')} response: {data}")

        return data.get("successful", False)
    except requests.RequestException as e:
        print(f"[Smart API] Exception posting member {member.get('membershipNumber')}: {e}")
        logger.exception(f"[Smart API] Exception posting member {member.get('membershipNumber')}: {e}")
        return False


def update_hais_member(membership_number: str, ann: str) -> bool:
    """
    Update HAIS API after successful sync and log response.
    """
    params = {
        "consumer_key": settings.HAIS_CONSUMER_KEY,
        "consumer_secret": settings.HAIS_CONSUMER_SECRET,
        "member_no": membership_number,
        "anniv": ann
    }
    try:
        response = requests.post(f"{settings.HAIS_API_BASE_URL}updateMembers/", params=params,
                                 headers={"Content-Length": "0"}, timeout=10)
        response.raise_for_status()
        print(f"[HAIS Update] Member {membership_number} response: {response.text}")
        logger.info(f"[HAIS Update] Member {membership_number} response: {response.text}")

        return "Successfully" in response.text
    except requests.RequestException as e:
        print(f"[HAIS Update] Exception updating member {membership_number}: {e}")
        logger.exception(f"[HAIS Update] Exception updating member {membership_number}: {e}")
        return False


def sync_all_members() -> Dict:
    """
    Main function to sync all members using working fetch_smart_token().
    """
    token = fetch_smart_token()
    if not token:
        return {"status": "error", "message": "Failed to get Smart token"}

    members = fetch_hais_members()
    if not members:
        return {"status": "error", "message": "No members to sync"}

    synced_count = 0
    for member in members:
        if post_member_to_smart(member, token):
            if update_hais_member(member.get("membershipNumber"), member.get("ann")):
                synced_count += 1

    print(f"[Sync Complete] Total members synced: {synced_count}")
    logger.info(f"[Sync Complete] Total members synced: {synced_count}")

    return {"status": "success", "synced_members": synced_count}



from django.http import JsonResponse
from django.db import connections, DatabaseError
from datetime import date
from datetime import date
from django.db import connections, DatabaseError, transaction
from django.http import JsonResponse
from smart.models import Corporate  # Your local Django model

def remote_corporate_api(request):
    """
    Fetch corporate records from remote SQL Server with current anniversary
    and save them to local Corporate table.
    """
    today = date.today()
    try:
        # Fetch from remote SQL Server
        with connections['external_mssql'].cursor() as cursor:
            cursor.execute("""
                SELECT c.*, ca.anniv, ca.start_date, ca.end_date
                FROM corporate c
                INNER JOIN corp_anniversary ca 
                    ON c.CORP_ID = ca.corp_id
                WHERE ca.start_date <= GETDATE()
                  AND ca.end_date >= GETDATE()
                  AND c.sync IS NULL
            """)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
    except DatabaseError as e:
        return JsonResponse({"error": str(e)}, status=500)

    staged_count = 0

    # Start a transaction for local Postgres
    with transaction.atomic():
        for row in rows:
            r = dict(zip(columns, row))

            # Save to local Corporate table
            corporate_obj, created = Corporate.objects.update_or_create(
                clnCode=r.get("CORP_ID"),
                defaults={
                    "companyName": r.get("CORPORATE"),
                    "clnPolCode": r.get("SCHEME"),
                    "anniv": r.get("anniv"),
                    "invoicePt": None,
                    "invContactEmail": r.get("EMAIL"),
                    "invPtcontactTel": r.get("TEL_NO") or r.get("MOBILE_NO"),
                    "polTypeId": None,
                    "userId": r.get("USER_ID"),
                    "clnPolType": None,
                    "policyNumber": r.get("policy_no"),
                    "startDate": r.get("date_entered"),
                    "endDate": None,
                    "statusReason": "NULL",
                    "cancelled": r.get("CANCELLED"),
                  
                }
            )
            staged_count += 1
       
    return JsonResponse({"status": "success", "staged_count": staged_count})
