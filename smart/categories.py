from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connections, DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connections, DatabaseError




from smart.models import BenefitCategory
@csrf_exempt
def fetch_unsynced_corp_groups(request):
    rows = []

    try:
        with connections["external_mssql"].cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1000 c.*, g.*, ca.anniv AS corp_anniv
                FROM corporate c
                INNER JOIN corp_groups g
                    ON c.CORP_ID = g.CORP_ID
                INNER JOIN corp_anniversary ca
                    ON c.CORP_ID = ca.corp_id
                WHERE g.sync IS NULL
                  AND g.anniv = ca.anniv
                ORDER BY c.CORP_ID
            """)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

    except DatabaseError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    # Convert to dicts
    data = [dict(zip(columns, row)) for row in rows]

   
    
    


  

    return JsonResponse({
        "status": "success",
        "count": len(data),
        "data": data
    })

import requests
import logging
from django.db import connections, DatabaseError, transaction
from django.conf import settings
from celery import shared_task

from smart.smartauth import fetch_smart_token
from smart.email import send_test_email
from .models import BenefitCategory, Corporate

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="benefit_categories_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

SMART_API_URL = "https://data.smartapplicationsgroup.com/api/v2/integqa/benefitCategories"
COUNTRY = "KE"
CUSTOMER_ID = settings.SMART_CUSTOMER_ID

def push_benefit_category_to_smart_api(obj: BenefitCategory):
    """
    Push a single BenefitCategory record to Smart API.
    """

    try:
        # Fetch token
        token = fetch_smart_token()
        if not token:
            msg = f"Failed to fetch Smart API token for category {obj.clnCatCode}"
            logger.error(msg)
            return {"success": False, "error": msg}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Prepare payload
        payload = {
            "catDesc": obj.catDesc,
            "userId": obj.userId,
            "clnCatCode": obj.clnCatCode,
            "clnPolCode": obj.clnPolCode,
            "customerid": CUSTOMER_ID,
            "country": COUNTRY
        }

        logger.info(f"[Benefit Category API] Pushing {obj.clnCatCode} ({obj.clnPolCode})")

        # POST request
        response = requests.post(
            SMART_API_URL,
            params=payload,  
            json=payload,     # Smart API wants both
            headers=headers,
            timeout=30
        )

        logger.info(
            f"[Benefit Category API] HTTP {response.status_code} for {obj.clnCatCode}: {response.text}"
        )

        response.raise_for_status()  # Raises error if not 200

        return {
            "success": True,
            "message": f"Successfully synced benefit {obj.clnCatCode}",
            "response": response.json()
        }

    except requests.exceptions.Timeout:
        msg = f"Timeout while pushing benefit {obj.clnCatCode}"
        logger.error(msg)
        return {"success": False, "error": msg}

    except requests.exceptions.RequestException as e:
        msg = f"Request failed for {obj.clnCatCode}: {str(e)}"
        logger.error(msg)
        return {"success": False, "error": msg}

    except Exception as e:
        msg = f"Unexpected error pushing benefit {obj.clnCatCode}: {str(e)}"
        logger.exception(msg)
        return {"success": False, "error": msg}

# @shared_task //this one is being used
def fetch_unsynced_benefit_categories():
    logger.info("[fetch_unsynced_benefit_categories] Starting sync process")

    try:
        with connections["external_mssql"].cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1000 
                    c.*, g.*, ca.anniv AS corp_anniv
                    
                FROM corporate c
                INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
                INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.corp_id
                WHERE g.sync IS NULL   AND GETDATE() BETWEEN ca.start_date AND ca.end_date
                  AND g.anniv = ca.anniv
            """)

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        logger.info(f"[fetch_unsynced_benefit_categories] Retrieved {len(rows)} rows")

    except DatabaseError as e:
        msg = f"Database fetch error: {str(e)}"
        logger.error(msg)
        return {"status": "error", "error": msg}

    staged_count = 0
    synced_count = 0
    failed_syncs = []

    for row in rows:
        r = dict(zip(columns, row))
        print(r)

        obj, created = BenefitCategory.objects.update_or_create(
            idx=r['idx'],  # lookup by idx only
            defaults={
                'clnPolCode': r["policy_no"],
                'clnCatCode': r["category"],
                'catDesc': r["category"],
                'userId': r["USER_ID"],
                'synced': False
            }
        )

        staged_count += 1

        # Push to API
        if not obj.synced:
            api_res = push_benefit_category_to_smart_api(obj)

            if api_res.get("success"):
                obj.synced = True
                obj.save(update_fields=["synced"])
                synced_count += 1

                logger.info(
                    f"[fetch_unsynced_benefit_categories] Synced {obj.clnCatCode}"
                )

               

            else:
                failed_syncs.append({
                    "clnCatCode": obj.clnCatCode,
                    "error": api_res.get("error"),
                })
                logger.error(
                    f"[fetch_unsynced_benefit_categories] Failed {obj.clnCatCode}: {api_res.get('error')}"
                )

    result = {
        "status": "success",
        "staged": staged_count,
        "synced": synced_count,
        "failed": len(failed_syncs),
        "failed_items": failed_syncs,
    }

    if failed_syncs:
        logger.warning(
            f"[fetch_unsynced_benefit_categories] Completed with {len(failed_syncs)} failures"
        )

    logger.info(
        f"[fetch_unsynced_benefit_categories] Finished: {staged_count} staged, {synced_count} synced"
    )

    return result

# from django.db import connections, DatabaseError
# from django.http import JsonResponse
# import logging

# logger = logging.getLogger(__name__)


# def fetch_unsynced_benefit_categories(request):

#     logger.info("[fetch_unsynced_benefit_categories] Starting per-corporate sync")

#     # -----------------------------------------
#     # 1. Load all corporates that exist locally
#     # -----------------------------------------
#     corporates = Corporate.objects.all().values_list("clnCode", flat=True)

#     if not corporates:
#         return JsonResponse({"status": "success", "message": "No corporates found."})

#     report = {
#         "status": "success",
#         "corporates_processed": 0,
#         "staged_total": 0,
#         "synced_total": 0,
#         "failed": []
#     }

#     # -----------------------------------------------------
#     # 2. Process corporate → Query MSSQL → Sync benefits
#     # -----------------------------------------------------
#     for corp_id in corporates:

#         logger.info(f"\n==== Processing Corporate: {corp_id} ====")

#         # -----------------------------------------
#         # 2A. Fetch benefit categories for THIS corporate only
#         # -----------------------------------------
#         try:
#             with connections["external_mssql"].cursor() as cursor:
#                 cursor.execute("""
#                     SELECT 
#                         c.CORP_ID,
#                         c.policy_no,
#                         g.idx,
#                         g.category,
#                         g.USER_ID,
#                         ca.anniv AS corp_anniv
#                     FROM corporate c
#                     INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
#                     INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.corp_id
#                     WHERE g.sync IS NULL
#                       AND GETDATE() BETWEEN ca.start_date AND ca.end_date
#                       AND g.anniv = ca.anniv
#                       AND c.CORP_ID = %s
#                 """, [str(corp_id)])

#                 columns = [col[0] for col in cursor.description]
#                 rows = cursor.fetchall()

#         except DatabaseError as e:
#             logger.error(f"MSSQL error for corp_id {corp_id}: {str(e)}")
#             continue  # skip to next corporate

#         if not rows:
#             logger.info(f"No unsynced benefit categories for corporate {corp_id}")
#             continue

#         staged = 0
#         synced = 0

#         # ----------------------------------------------------
#         # 3. Sync each benefit category for this corporate
#         # ----------------------------------------------------
#         for row in rows:
#             r = dict(zip(columns, row))

#             obj, created = BenefitCategory.objects.update_or_create(
#                 idx=r["idx"],  # unique identifier
#                 defaults={
#                     "clnPolCode": r["policy_no"],
#                     "clnCatCode": r["category"],
#                     "catDesc": r["category"],
#                     "userId": r["USER_ID"],
#                     "synced": False
#                 }
#             )

#             staged += 1
#             report["staged_total"] += 1

#             # Push to API
#             if not obj.synced:
#                 api_res = push_benefit_category_to_smart_api(obj, corp_id=str(corp_id))

#                 if api_res.get("success"):
#                     obj.synced = True
#                     obj.save(update_fields=["synced"])

#                     synced += 1
#                     report["synced_total"] += 1

#                     logger.info(
#                         f"[OK] Corporate {corp_id} → Benefit {obj.clnCatCode} synced"
#                     )

#                 else:
#                     error_msg = api_res.get("error", "Unknown error")

#                     report["failed"].append({
#                         "corp_id": corp_id,
#                         "clnCatCode": obj.clnCatCode,
#                         "error": error_msg
#                     })

#                     logger.error(
#                         f"[FAILED] Corporate {corp_id} → {obj.clnCatCode}: {error_msg}"
#                     )

#         logger.info(
#             f"[CORPORATE SUMMARY] {corp_id}: {staged} staged, {synced} synced"
#         )

#         report["corporates_processed"] += 1

#     return JsonResponse(report)
