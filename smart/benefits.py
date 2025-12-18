import logging
from celery import shared_task
from django.db import connections, transaction, DatabaseError
from engine.s_engine import push_benefits_to_smart_api
from smart.models import Benefit

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="benefit_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)




from django.db import connections, transaction, DatabaseError
import logging
# from myapp.models import Benefit
# from myapp.api import push_benefits_to_smart_api

logger = logging.getLogger(__name__)

def fetch_and_push_unsynced_benefits_task():
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
                    "CatCode": x["category"],
                    "clnBenCode": x["code"],
                    "clnPolCode": x["policy_no"],
                    "benTypeId": x["sharing"],
                    "subLimitAmt": x["limit"],
                    "serviceType": x["code"],
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

    # Push all staged benefits in bulk to Smart API
    api_result = push_benefits_to_smart_api(staged_benefits)

    synced_count = 0
    failed_syncs = []

    if api_result.get("success"):
        with transaction.atomic():
            for benefit in staged_benefits:
                benefit.synced = True
                benefit.save(update_fields=["synced"])
                synced_count += 1

        # Optionally, update MSSQL corp_groups.sync = 1 in bulk here
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

