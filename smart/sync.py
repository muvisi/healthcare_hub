
# import requests
# import logging
# from django.db import connections, DatabaseError, transaction
# from django.conf import settings
# from celery import shared_task

# from smart.smartauth import fetch_smart_token
# from smart.email import send_test_email
# from .models import BenefitCategory

# logger = logging.getLogger(__name__)
# logging.basicConfig(
#     filename="benefit_categories_sync.log",
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# SMART_API_URL = "https://data.smartapplicationsgroup.com/api/v2/integqa/benefitCategories"
# COUNTRY = "KE"
# CUSTOMER_ID = settings.SMART_CUSTOMER_ID

# def push_benefit_category_to_smart_api(obj: BenefitCategory):
#     """
#     Push a single BenefitCategory record to Smart API.
#     """

#     try:
#         # Fetch token
#         token = fetch_smart_token()
#         if not token:
#             msg = f"Failed to fetch Smart API token for category {obj.clnCatCode}"
#             logger.error(msg)
#             return {"success": False, "error": msg}

#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }

#         # Prepare payload
#         payload = {
#             "catDesc": obj.catDesc,
#             "userId": obj.userId,
#             "clnCatCode": obj.clnCatCode,
#             "clnPolCode": obj.clnPolCode,
#             "customerid": obj.customerid,
#             "country": obj.country,
#         }

#         logger.info(f"[Benefit Category API] Pushing {obj.clnCatCode} ({obj.clnPolCode})")

#         # POST request
#         response = requests.post(
#             SMART_API_URL,
#             params=payload,  
#             json=payload,     # Smart API wants both
#             headers=headers,
#             timeout=30
#         )

#         logger.info(
#             f"[Benefit Category API] HTTP {response.status_code} for {obj.clnCatCode}: {response.text}"
#         )

#         response.raise_for_status()  # Raises error if not 200

#         return {
#             "success": True,
#             "message": f"Successfully synced benefit {obj.clnCatCode}",
#             "response": response.json()
#         }

#     except requests.exceptions.Timeout:
#         msg = f"Timeout while pushing benefit {obj.clnCatCode}"
#         logger.error(msg)
#         return {"success": False, "error": msg}

#     except requests.exceptions.RequestException as e:
#         msg = f"Request failed for {obj.clnCatCode}: {str(e)}"
#         logger.error(msg)
#         return {"success": False, "error": msg}

#     except Exception as e:
#         msg = f"Unexpected error pushing benefit {obj.clnCatCode}: {str(e)}"
#         logger.exception(msg)
#         return {"success": False, "error": msg}

# @shared_task
# def fetch_unsynced_benefit_categories():
#     logger.info("[fetch_unsynced_benefit_categories] Starting sync process")

#     try:
#         with connections["external_mssql"].cursor() as cursor:
#             cursor.execute("""
#                 SELECT TOP 1000 
#                     c.CORP_ID,
#                     c.USER_ID,
#                     g.policy_no,
#                     g.category,
#                     g.anniv,
#                     ca.anniv as corp_anniv
#                 FROM corporate c
#                 INNER JOIN corp_groups g ON c.CORP_ID = g.CORP_ID
#                 INNER JOIN corp_anniversary ca ON c.CORP_ID = ca.corp_id
#                 WHERE g.sync IS NULL 
#                   AND g.anniv = ca.anniv
#             """)

#             columns = [col[0] for col in cursor.description]
#             rows = cursor.fetchall()

#         logger.info(f"[fetch_unsynced_benefit_categories] Retrieved {len(rows)} rows")

#     except DatabaseError as e:
#         msg = f"Database fetch error: {str(e)}"
#         logger.error(msg)
#         return {"status": "error", "error": msg}

#     staged_count = 0
#     synced_count = 0
#     failed_syncs = []

#     with transaction.atomic():
#         for row in rows:
#             r = dict(zip(columns, row))

#             # Stage locally
#             obj, created = BenefitCategory.objects.update_or_create(
#                 clnPolCode=r["policy_no"],
#                 clnCatCode=r["category"],
#                 defaults={
#                     "catDesc": r["category"],
#                     "userId": r["USER_ID"],
#                     "customerid": r["CORP_ID"],
#                     "country": COUNTRY,
#                     "synced": False,
#                 }
#             )

#             staged_count += 1

#             # Push to API
#             if not obj.synced:
#                 api_res = push_benefit_category_to_smart_api(obj)

#                 if api_res.get("success"):
#                     obj.synced = True
#                     obj.save(update_fields=["synced"])
#                     synced_count += 1

#                     logger.info(
#                         f"[fetch_unsynced_benefit_categories] Synced {obj.clnCatCode}"
#                     )
#                 else:
#                     failed_syncs.append({
#                         "clnCatCode": obj.clnCatCode,
#                         "error": api_res.get("error"),
#                     })
#                     logger.error(
#                         f"[fetch_unsynced_benefit_categories] Failed {obj.clnCatCode}: {api_res.get('error')}"
#                     )

#     # Email admin
#     send_test_email(staged_count)

#     result = {
#         "status": "success",
#         "staged": staged_count,
#         "synced": synced_count,
#         "failed": len(failed_syncs),
#         "failed_items": failed_syncs,
#     }

#     if failed_syncs:
#         logger.warning(
#             f"[fetch_unsynced_benefit_categories] Completed with {len(failed_syncs)} failures"
#         )

#     logger.info(
#         f"[fetch_unsynced_benefit_categories] Finished: {staged_count} staged, {synced_count} synced"
#     )

#     return result
