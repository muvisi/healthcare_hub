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
from smart.schemes import push_scheme_to_smart_api
from smart.smartauth import fetch_smart_token

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="smart_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
def fetch_new_schemes():
    logger.info("[fetch_new_schemes] Starting scheme fetch and sync process")

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

        logger.info(f"[fetch_new_schemes] Fetched {len(rows)} new schemes from MSSQL")

    except DatabaseError as e:
        error_msg = f"Database error while fetching schemes: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    staged_count = 0
    synced_count = 0
    failed_syncs = []

    with transaction.atomic():
        for row in rows:
            data = dict(zip(columns, row))

            corporate, created = Corporate.objects.update_or_create(
                clnCode=data.get("CORP_ID"),
                defaults={
                    "companyName": data.get("CORPORATE"),
                    "clnPolCode": data.get("policy_no"),
                    "anniv": data.get("anniv"),
                    "invoicePt": None,
                    "invContactEmail": data.get("EMAIL"),
                    "invPtcontactTel": data.get("TEL_NO") or data.get("MOBILE_NO"),
                    "polTypeId": None,
                    "userId": data.get("USER_ID"),
                    "clnPolType": None,
                    "policyNumber": data.get("policy_no"),
                    "startDate": data.get("start_date"),
                    "endDate": data.get("end_date"),
                    "statusReason": "NULL",
                    "cancelled": data.get("CANCELLED"),
                    "synced": False,
                }
            )

            staged_count += 1

            if not corporate.synced:
                logger.info(f"[fetch_new_schemes] Pushing scheme {corporate.clnPolCode} to Smart API")

                api_result = push_scheme_to_smart_api(corporate)

                if api_result.get("success"):
                    corporate.synced = True
                    corporate.save(update_fields=["synced"])

                    try:
                        with connections['external_mssql'].cursor() as cursor:
                            cursor.execute("""
                                UPDATE corporate SET sync = 1 WHERE CORP_ID = %s
                            """, [data.get("CORP_ID")])
                        logger.info(f"[fetch_new_schemes] Updated MSSQL sync flag for CORP_ID {data.get('CORP_ID')}")
                    except DatabaseError as e:
                        logger.error(
                            f"[fetch_new_schemes] FAILED to update sync flag for CORP_ID {data.get('CORP_ID')}: {str(e)}"
                        )

                    synced_count += 1
                else:
                    error_msg = api_result.get("error", "Unknown error")
                    failed_syncs.append({
                        "clnPolCode": corporate.clnPolCode,
                        "error": error_msg,
                    })
                    logger.error(
                        f"[fetch_new_schemes] Sync FAILED for scheme {corporate.clnPolCode}: {error_msg}"
                    )

    try:
        send_test_email(staged_count)
        logger.info("[fetch_new_schemes] Email summary sent successfully")
    except Exception as e:
        logger.error(f"[fetch_new_schemes] Email sending failed: {str(e)}")

    response = {
        "status": "success",
        "staged_count": staged_count,
        "synced_count": synced_count,
        "failed_count": len(failed_syncs),
    }

    if failed_syncs:
        response["failed_syncs"] = failed_syncs
        logger.warning(f"[fetch_new_schemes] Completed with {len(failed_syncs)} sync failures")

    logger.info(
        f"[fetch_new_schemes] DONE → {staged_count} staged | {synced_count} synced | {len(failed_syncs)} failed"
    )

    return response
