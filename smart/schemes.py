import requests
import json
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from django.db import connections, DatabaseError, transaction
from django.conf import settings
from celery import shared_task

from smart.models import Benefit, Corporate
from smart.email import send_test_email
from smart.smartauth import fetch_smart_token

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="smart_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def push_scheme_to_smart_api(corporate: Corporate) -> Dict[str, any]:
    """
    Push a single corporate scheme to Smart API.
    
    Args:
        corporate: Corporate model instance to push to API
        
    Returns:
        Dict with 'success' boolean and 'message' or 'error' string
    """
    try:
        # Fetch authentication token
        token = fetch_smart_token()
        if not token:
            error_msg = f"Failed to fetch Smart API token for scheme {corporate.clnPolCode}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Prepare API URL and headers
        url = settings.SMART_SCHEMES_API_URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Prepare payload with corporate data
        # Convert all values to JSON-serializable types
        payload = {
            "companyName": str(corporate.companyName or ""),
            "clnPolCode": str(corporate.clnPolCode or ""),
            "startDate": corporate.startDate.strftime("%Y-%m-%d") if corporate.startDate else "",
            "endDate": corporate.endDate.strftime("%Y-%m-%d") if corporate.endDate else "",
            "polTypeId": int(corporate.polTypeId) if corporate.polTypeId and str(corporate.polTypeId).isdigit() else 1,
            "userId": str(corporate.userId or ""),
            "countryCode": str(corporate.countryCode or settings.COUNTRY_CODE),
            "policyCurrencyId": str(settings.POLICY_CURRENCY_ID),
            "anniv": int(corporate.anniv) if corporate.anniv else 1,
            "customerId": str(settings.SMART_CUSTOMER_ID)
        }
        
        # Prepare query parameters (same as payload for this API)
        params = {
            "companyName": payload["companyName"],
            "clnPolCode": payload["clnPolCode"],
            "startDate": payload["startDate"],
            "endDate": payload["endDate"],
            "polTypeId": payload["polTypeId"],
            "userId": payload["userId"],
            "countryCode": payload["countryCode"],
            "policyCurrencyId": payload["policyCurrencyId"],
            "anniv": payload["anniv"],
            "customerid": payload["customerId"]
        }
        
        logger.info(f"[Smart Schemes API] Pushing scheme {corporate.clnPolCode} to API")
        
        # Make POST request to Smart API
        response = requests.post(
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Log response
        logger.info(f"[Smart Schemes API] HTTP {response.status_code} for {corporate.clnPolCode}: {response.text}")
        
        # Check for successful response
        response.raise_for_status()
        
        # Parse response
        response_data = response.json()
        
        return {
            "success": True,
            "message": f"Successfully pushed scheme {corporate.clnPolCode}",
            "response": response_data
        }
        
    except requests.exceptions.Timeout:
        error_msg = f"Timeout while pushing scheme {corporate.clnPolCode} to Smart API"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error for scheme {corporate.clnPolCode}: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected error pushing scheme {corporate.clnPolCode}: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "error": error_msg}


# @shared_task //is being used
from django.db import connections, DatabaseError, transaction
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def fetch_new_schemes(request):
    """
    Fetch corporate records from remote SQL Server with current anniversary,
    save them to local Corporate table, push to Smart API, and mark synced.
    """

    logger.info("[fetch_new_schemes] Starting scheme fetch and sync process")

    # ------------------------------
    # Fetch from external MSSQL
    # ------------------------------
    try:
        with connections['external_mssql'].cursor() as cursor:
            cursor.execute("""
                SELECT c.*, ca.anniv, ca.start_date, ca.end_date
                FROM corporate c
                INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.corp_id
                WHERE ca.start_date <= GETDATE()
                  AND ca.end_date >= GETDATE()
                  AND c.sync IS NULL
            """)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        logger.info(f"[fetch_new_schemes] Fetched {len(rows)} schemes from MSSQL")

    except DatabaseError as e:
        error_msg = f"Database error while fetching schemes: {str(e)}"
        logger.error(error_msg)
        return JsonResponse({"status": "error", "error": error_msg}, status=500)

    staged_count = 0
    synced_count = 0
    failed_syncs = []

    # ------------------------------
    # Process each corporate record
    # ------------------------------
    with transaction.atomic():
        for row in rows:
            r = dict(zip(columns, row))

            # Save or update corporate record locally
            corporate, created = Corporate.objects.update_or_create(
                clnCode=r.get("CORP_ID"),
                defaults={
                    "companyName": r.get("CORPORATE"),
                    "clnPolCode": r.get("policy_no"),
                    "anniv": r.get("anniv"),
                    "invoicePt": None,
                    "invContactEmail": r.get("EMAIL"),
                    "invPtcontactTel": r.get("TEL_NO") or r.get("MOBILE_NO"),
                    "polTypeId": None,
                    "userId": r.get("USER_ID"),
                    "clnPolType": None,
                    "policyNumber": r.get("policy_no"),
                    "startDate": r.get("start_date"),
                    "endDate": r.get("end_date"),
                    "statusReason": "NULL",
                    "cancelled": r.get("CANCELLED"),
                    "synced": False,
                }
            )

            staged_count += 1

            # Push to Smart API only if not already synced
            if not corporate.synced:
                logger.info(f"[fetch_new_schemes] Pushing scheme {corporate.clnPolCode} to Smart API")

                api_result = push_scheme_to_smart_api(corporate)

                if api_result.get("success"):
                    # Mark local record as synced
                    corporate.synced = True
                    corporate.save(update_fields=["synced"])

                    # Update external MSSQL sync flag
                    try:
                        with connections['external_mssql'].cursor() as cursor:
                            cursor.execute(
                                "UPDATE corporate SET sync = 1 WHERE CORP_ID = %s",
                                [r.get("CORP_ID")]
                            )
                    except DatabaseError as e:
                        logger.error(
                            f"Failed to update sync in external corporate table for CORP_ID {r.get('CORP_ID')}: {str(e)}"
                        )

                    synced_count += 1
                    logger.info(f"[fetch_new_schemes] Successfully synced scheme {corporate.clnPolCode}")

                else:
                    # Track failed sync
                    failed_syncs.append({
                        "clnPolCode": corporate.clnPolCode,
                        "error": api_result.get("error", "Unknown error"),
                    })

                    logger.error(
                        f"[fetch_new_schemes] Failed to sync scheme {corporate.clnPolCode}: "
                        f"{api_result.get('error')}"
                    )

    # ------------------------------
    # Send notification email
    # ------------------------------
    # send_test_email(staged_count)

    # ------------------------------
    # Build JSON response
    # ------------------------------
    result = {
        "status": "success",
        "staged_count": staged_count,
        "synced_count": synced_count,
        "failed_count": len(failed_syncs),
    }

    if failed_syncs:
        result["failed_syncs"] = failed_syncs

    logger.warning(f"[fetch_new_schemes] Completed with {len(failed_syncs)} failed syncs")
    logger.info(f"[fetch_new_schemes] Process completed: {staged_count} staged, {synced_count} synced to API")

    return JsonResponse(result, safe=False)





#