# @shared_task


import requests
import logging
from django.db import connections, DatabaseError, transaction
from django.conf import settings
from celery import shared_task

from engine.s_engine import push_benefits_to_smart_api
from smart.categories import push_benefit_category_to_smart_api
from smart.models import Benefit, BenefitCategory
from smart.smartauth import fetch_smart_token
from smart.email import send_test_email
# from .models import BenefitCategory

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="benefit_categories_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)




from django.db import connections, transaction, DatabaseError
# from myapp.models import BenefitCategory
# from myapp.api import push_benefits_to_smart_api
import logging

logger = logging.getLogger(__name__)

def fetch_unsynced_benefit(corp_id: str):
    logger.info(f"[fetch_unsynced_benefit] Starting sync process for CORP_ID={corp_id}")

    try:
        with connections["external_mssql"].cursor() as cursor:
            cursor.execute("""
                SELECT g.*, ca.anniv AS corp_anniv, c.policy_no
                FROM corp_groups g
                INNER JOIN corporate c ON g.CORP_ID = c.CORP_ID
                INNER JOIN corp_anniversary ca ON g.CORP_ID = ca.corp_id
                WHERE g.sync IS NULL
                  AND g.CORP_ID = %s
                  AND GETDATE() BETWEEN ca.start_date AND ca.end_date
                  AND g.anniv = ca.anniv
            """, [corp_id])

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        logger.info(f"[fetch_unsynced_benefit_categories] Retrieved {len(rows)} unsynced benefits")

    except DatabaseError as e:
        msg = f"Database fetch error: {str(e)}"
        logger.error(msg)
        return {"status": "error", "error": msg}

    if not rows:
        return {"status": "success", "message": "No unsynced benefits found", "staged": 0, "synced": 0}

    # Stage the benefits locally
    staged_benefits = []
    with transaction.atomic():
        for row in rows:
            r = dict(zip(columns, row))

            obj, created = BenefitCategory.objects.update_or_create(
                idx=r['idx'],  # Use idx as unique identifier
                defaults={
                    'clnPolCode': r["policy_no"],
                    'clnCatCode': r["category"],
                    'catDesc': r["category"],
                    'userId': r["USER_ID"],
                    'synced': False
                }
            )
            staged_benefits.append(obj)

    staged_count = len(staged_benefits)

    # Push all staged benefits in bulk
    api_result = push_benefits_to_smart_api(staged_benefits)

    synced_count = 0
    failed_syncs = []

    if api_result.get("success"):
        # Mark all staged benefits as synced
        with transaction.atomic():
            for benefit in staged_benefits:
                benefit.synced = True
                benefit.save(update_fields=["synced"])
                synced_count += 1

            # Update external MSSQL sync flag
            try:
                with connections["external_mssql"].cursor() as cursor:
                    idx_list = [b.idx for b in staged_benefits]
                    # Update in bulk using IN clause
                    format_strings = ','.join(['%s'] * len(idx_list))
                    cursor.execute(f"UPDATE corp_groups SET sync = 1 WHERE idx IN ({format_strings})", idx_list)
            except DatabaseError as e:
                logger.error(f"Failed to update corp_groups.sync for bulk idx: {str(e)}")

    else:
        # If bulk push failed, track all as failed
        failed_syncs = [{"clnCatCode": b.clnCatCode, "error": api_result.get("error")} for b in staged_benefits]
        logger.error(f"[fetch_unsynced_benefit_categories] Bulk push failed: {api_result.get('error')}")

    result = {
        "status": "success" if synced_count else "error",
        "staged": staged_count,
        "synced": synced_count,
        "failed": len(failed_syncs),
        "failed_items": failed_syncs
    }

    logger.info(f"[fetch_unsynced_benefit_categories] Finished: {staged_count} staged, {synced_count} synced")
    return result



from django.db import connections, transaction, DatabaseError
import logging

logger = logging.getLogger(__name__)
import logging
from django.db import connections, transaction, DatabaseError
from celery import shared_task
# from myapp.models import Benefit
# from myapp.api import push_benefits_to_smart_api

logger = logging.getLogger(__name__)

@shared_task
def fetch_and_push_unsynced_benefits():
    logger.info("[TASK] fetch_and_push_unsynced_benefits started...")

    query = """
        SELECT 
            c.*, 
            g.*, 
            ca.*, 
            b.*
        FROM corporate c
        INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
        INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.CORP_ID
        INNER JOIN benefit b ON g.benefit = b.code
        WHERE g.sync IS NULL
          AND GETDATE() BETWEEN ca.start_date AND ca.end_date
        ORDER BY c.CORP_ID;
    """

    try:
        with connections["external_mssql"].cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        logger.info(f"[fetch_unsynced_benefits] Retrieved {len(rows)} rows")

    except DatabaseError as e:
        logger.error(f"DB Error: {str(e)}")
        return {"status": "error", "error": str(e)}

    staged_benefits = []

    with transaction.atomic():
        for row in rows:
            x = dict(zip(columns, row))
            obj, created = Benefit.objects.update_or_create(
                idx=x["idx"],
                defaults={
                    "clnPolCode": x["policy_no"],
                    "catCode": x["category"],
                    "benTypeId": x["sharing"],
                    "subLimitAmt": x["limit"],
                    "serviceType": x["code"],
                    "clnBenCode": x["code"],
                    "benefitDesc": x["benefit"],
                    "benLinked2Tqcode": x.get("sub_benefit"),
                    "memAssignedBenefit": x.get("class"),
                    "userId": x["USER_ID"],
                    "synced": False
                }
            )
            staged_benefits.append(obj)

    staged_count = len(staged_benefits)
    logger.info(f"[fetch_unsynced_benefits] Staged {staged_count} benefits")

    if staged_count == 0:
        return {"status": "success", "staged": 0, "synced": 0}

    # Bulk push to Smart API
    api_result = push_benefits_to_smart_api(staged_benefits)

    synced_count = 0
    failed_syncs = []

    if api_result.get("success"):
        with transaction.atomic():
            for benefit in staged_benefits:
                benefit.synced = True
                benefit.save(update_fields=["synced"])
                synced_count += 1

        # Update MSSQL corp_groups.sync for all pushed benefits
        try:
            with connections["external_mssql"].cursor() as cursor:
                idx_list = [b.idx for b in staged_benefits]
                format_strings = ','.join(['%s'] * len(idx_list))
                cursor.execute(f"UPDATE corp_groups SET sync = 1 WHERE idx IN ({format_strings})", idx_list)
        except DatabaseError as e:
            logger.error(f"Failed to update corp_groups.sync in MSSQL: {str(e)}")

    else:
        failed_syncs = [{"clnBenCode": b.clnBenCode, "error": api_result.get("error")} for b in staged_benefits]
        logger.error(f"[fetch_unsynced_benefits] Bulk push failed: {api_result.get('error')}")

    logger.info(f"[fetch_unsynced_benefits] Finished: {staged_count} staged, {synced_count} synced")

    return {
        "status": "success" if synced_count else "error",
        "staged": staged_count,
        "synced": synced_count,
        "failed": len(failed_syncs),
        "failed_items": failed_syncs
    }
