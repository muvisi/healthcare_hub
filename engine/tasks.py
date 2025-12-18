# @shared_task


import requests
import logging
from django.db import connections, DatabaseError, transaction
from django.conf import settings
from celery import shared_task

from engine.s_engine import push_benefit_category_to_smart_api, push_benefits_to_smart_api
# from smart.categories import push_benefit_category_to_smart_api
from smart.models import Benefit, BenefitCategory, Corporate
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

import logging

logger = logging.getLogger(__name__)



from django.db import connections, transaction, DatabaseError
import logging

logger = logging.getLogger(__name__)
import logging
from django.db import connections, transaction, DatabaseError
from celery import shared_task
# from myapp.models import Benefit
# from myapp.api import push_benefits_to_smart_api

logger = logging.getLogger(__name__)

# @shared_task
# def fetch_and_push_unsynced_benefits():
#     logger.info("[TASK] fetch_and_push_unsynced_benefits started...")

#     query = """
#         SELECT top 10
#             c.*, 
#             g.*, 
#             ca.*, 
#             b.*
#         FROM corporate c
#         INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
#         INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.CORP_ID
#         INNER JOIN benefit b ON g.benefit = b.code
#         WHERE g.sync IS NULL
#           AND GETDATE() BETWEEN ca.start_date AND ca.end_date
#         ORDER BY c.CORP_ID;
#     """

#     try:
#         with connections["external_mssql"].cursor() as cursor:
#             cursor.execute(query)
#             columns = [col[0] for col in cursor.description]
#             rows = cursor.fetchall()

#         logger.info(f"[fetch_unsynced_benefits] Retrieved {len(rows)} rows")

#     except DatabaseError as e:
#         logger.error(f"DB Error: {str(e)}")
#         return {"status": "error", "error": str(e)}

#     staged_benefits = []

#     with transaction.atomic():
#         for row in rows:
#             x = dict(zip(columns, row))
#             obj, created = Benefit.objects.update_or_create(
#                 idx=x["idx"],
#                 defaults={
#                     "clnPolCode": x["policy_no"],
#                     "catCode": x["category"],
#                     "benTypeId": x["sharing"],
#                     "subLimitAmt": x["limit"],
#                     "serviceType": x["CODE"],
#                     "clnBenCode": x["CODE"],
#                     "benefitDesc": x["benefit"],
#                     "benLinked2Tqcode": x.get("sub_benefit"),
#                     "memAssignedBenefit": x.get("class"),
#                     "userId": x["USER_ID"],
#                     "synced": False
#                 }
#             )
#             staged_benefits.append(obj)

#     staged_count = len(staged_benefits)
#     logger.info(f"[fetch_unsynced_benefits] Staged {staged_count} benefits")

#     if staged_count == 0:
#         return {"status": "success", "staged": 0, "synced": 0}

#     # Bulk push to Smart API
#     for x in staged_benefits:
#         print("staged",x)
#     api_result = push_benefits_to_smart_api(staged_benefits)

#     synced_count = 0
#     failed_syncs = []

#     if api_result.get("success"):
#         with transaction.atomic():
#             for benefit in staged_benefits:
#                 benefit.synced = True
#                 benefit.save(update_fields=["synced"])
#                 synced_count += 1

#         # Update MSSQL corp_groups.sync for all pushed benefits
#         try:
#             with connections["external_mssql"].cursor() as cursor:
#                 idx_list = [b.idx for b in staged_benefits]
#                 format_strings = ','.join(['%s'] * len(idx_list))
#                 cursor.execute(f"UPDATE corp_groups SET sync = 1 WHERE idx IN ({format_strings})", idx_list)
#         except DatabaseError as e:
#             logger.error(f"Failed to update corp_groups.sync in MSSQL: {str(e)}")

#     else:
#         failed_syncs = [{"clnBenCode": b.clnBenCode, "error": api_result.get("error")} for b in staged_benefits]
#         logger.error(f"[fetch_unsynced_benefits] Bulk push failed: {api_result.get('error')}")

#     logger.info(f"[fetch_unsynced_benefits] Finished: {staged_count} staged, {synced_count} synced")

#     return {
#         "status": "success" if synced_count else "error",
#         "staged": staged_count,
#         "synced": synced_count,
#         "failed": len(failed_syncs),
#         "failed_items": failed_syncs
#     }


from django.db import connections, DatabaseError
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def fetch_unsynced_benefit_categories_final(request):

    logger.info("[fetch_unsynced_benefit_categories] Starting per-corporate sync")

    # -----------------------------------------
    # 1. Load all corporates that exist locally
    # -----------------------------------------
    corporates = Corporate.objects.all().values_list("clnCode", flat=True)

    if not corporates:
        return JsonResponse({"status": "success", "message": "No corporates found."})

    report = {
        "status": "success",
        "corporates_processed": 0,
        "staged_total": 0,
        "synced_total": 0,
        "failed": []
    }

    # -----------------------------------------------------
    # 2. Process corporate → Query MSSQL → Sync benefits
    # -----------------------------------------------------
    for corp_id in corporates:

        logger.info(f"\n==== Processing Corporate: {corp_id} ====")
# from myapp.models import BenefitCategory
# from myapp.api import push_benefits_to_smart_api
        # -----------------------------------------
        # 2A. Fetch benefit categories for THIS corporate only
        # -----------------------------------------
        try:
            with connections["external_mssql"].cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.CORP_ID,
                        c.policy_no,
                        g.idx,
                        g.category,
                        g.USER_ID,
                        ca.anniv AS corp_anniv
                    FROM corporate c
                    INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
                    INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.corp_id
                    WHERE g.sync IS NULL
                      AND GETDATE() BETWEEN ca.start_date AND ca.end_date
                      AND g.anniv = ca.anniv
                      AND c.CORP_ID = %s
                """, [str(corp_id)])

                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

        except DatabaseError as e:
            logger.error(f"MSSQL error for corp_id {corp_id}: {str(e)}")
            continue  # skip to next corporate

        if not rows:
            logger.info(f"No unsynced benefit categories for corporate {corp_id}")
            continue

        staged = 0
        synced = 0

        # ----------------------------------------------------
        # 3. Sync each benefit category for this corporate
        # ----------------------------------------------------
        for row in rows:
            r = dict(zip(columns, row))

            obj, created = BenefitCategory.objects.update_or_create(
                idx=r["idx"],  # unique identifier
                defaults={
                    "clnPolCode": r["policy_no"],
                    "clnCatCode": r["category"],
                    "catDesc": r["category"],
                    "userId": r["USER_ID"],
                    "synced": False
                }
            )

            staged += 1
            report["staged_total"] += 1

            # Push to API
            if not obj.synced:
                api_res = push_benefit_category_to_smart_api(obj, corp_id=str(corp_id))

                if api_res.get("success"):
                    obj.synced = True
                    obj.save(update_fields=["synced"])

                    synced += 1
                    report["synced_total"] += 1

                    logger.info(
                        f"[OK] Corporate {corp_id} → Benefit {obj.clnCatCode} synced"
                    )

                else:
                    error_msg = api_res.get("error", "Unknown error")

                    report["failed"].append({
                        "corp_id": corp_id,
                        "clnCatCode": obj.clnCatCode,
                        "error": error_msg
                    })

                    logger.error(
                        f"[FAILED] Corporate {corp_id} → {obj.clnCatCode}: {error_msg}"
                    )

        logger.info(
            f"[CORPORATE SUMMARY] {corp_id}: {staged} staged, {synced} synced"
        )

        report["corporates_processed"] += 1

    return JsonResponse(report)
from django.db import connections, DatabaseError, transaction
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def fetch_and_push_unsynced_benefits_final(request):

    logger.info("[TASK] fetch_and_push_unsynced_benefits started (per corporate)...")

    # -----------------------------------------
    # 1. Get list of all corporates in Django
    # -----------------------------------------
    corporates = Corporate.objects.all().values_list("clnCode", flat=True)

    if not corporates:
        return JsonResponse({"status": "success", "message": "No corporates found."})

    report = {
        "status": "success",
        "corporates_processed": 0,
        "staged_total": 0,
        "synced_total": 0,
        "failed": []
    }

    # -----------------------------------------------------
    # 2. Process each corporate ONE AT A TIME
    # -----------------------------------------------------
    for corp_id in corporates:

        logger.info(f"\n========== PROCESSING CORPORATE {corp_id} =============")

        # -----------------------------------------
        # 2A. Fetch ALL unsynced benefits for THIS corporate only
        # -----------------------------------------
        try:
            with connections["external_mssql"].cursor() as cursor:
                cursor.execute("""
                    SELECT
                        c.CORP_ID,
                        c.policy_no,
                        g.idx,
                        g.category,
                        g.USER_ID,
                        g.class,
                        g.sharing,
                        g.limit,
                        g.sub_benefit,
                        b.CODE,
                        b.benefit
                    FROM corporate c
                    INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
                    INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.CORP_ID
                    INNER JOIN benefit b ON g.benefit = b.code
                    WHERE g.sync IS NULL
                      AND GETDATE() BETWEEN ca.start_date AND ca.end_date
                      AND c.CORP_ID = %s
                """, [str(corp_id)])

                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

        except DatabaseError as e:
            logger.error(f"[ERROR] MSSQL fetch failed for corporate {corp_id}: {str(e)}")
            continue

        if not rows:
            logger.info(f"No unsynced benefits for corporate {corp_id}")
            continue

        logger.info(f"[INFO] Corporate {corp_id}: Retrieved {len(rows)} unsynced benefits")

        staged = []
        synced_count = 0

        # -----------------------------------------
        # 3. Stage (store/update) each benefit in Django
        # -----------------------------------------
        with transaction.atomic():
            for row in rows:
                r = dict(zip(columns, row))

                benefit_obj, created = Benefit.objects.update_or_create(
                    idx=r["idx"],
                    defaults={
                        "clnPolCode": r["policy_no"],
                        "catCode": r["category"],
                        "benTypeId": r["sharing"],
                        "subLimitAmt": r["limit"],
                        "serviceType": r["CODE"],
                        "clnBenCode": r["CODE"],
                        "benefitDesc": r["benefit"],
                        "benLinked2Tqcode": r.get("sub_benefit"),
                        "memAssignedBenefit": r.get("class"),
                        "userId": r["USER_ID"],
                        "synced": False
                    }
                )
                staged.append(benefit_obj)

        staged_count = len(staged)
        report["staged_total"] += staged_count

        logger.info(f"[STAGED] Corporate {corp_id}: {staged_count} benefits stored locally")

        if staged_count == 0:
            continue

        # -----------------------------------------
        # 4. Push benefits for THIS corporate only
        # -----------------------------------------
        api_result = push_benefits_to_smart_api(staged, corp_id=str(corp_id))

        if api_result.get("success"):
            # Mark as synced
            with transaction.atomic():
                for ben in staged:
                    ben.synced = True
                    ben.save(update_fields=["synced"])
                    synced_count += 1

            # Update MSSQL sync flags
            try:
                with connections["external_mssql"].cursor() as cursor:
                    idx_list = [b.idx for b in staged]
                    placeholders = ",".join(["%s"] * len(idx_list))

                    cursor.execute(
                        f"UPDATE corp_groups SET sync = 1 WHERE idx IN ({placeholders})",
                        idx_list
                    )
            except DatabaseError as e:
                logger.error(f"[ERROR] Failed to update MSSQL sync for corporate {corp_id}: {str(e)}")

            logger.info(f"[SYNC OK] Corporate {corp_id}: {synced_count} synced")

            report["synced_total"] += synced_count

        else:
            # API failed for this corporate
            error_msg = api_result.get("error", "Unknown API error")

            logger.error(f"[SYNC FAIL] Corporate {corp_id}: {error_msg}")

            for ben in staged:
                report["failed"].append({
                    "corp_id": corp_id,
                    "clnBenCode": ben.clnBenCode,
                    "error": error_msg
                })

        report["corporates_processed"] += 1

    return JsonResponse(report)
