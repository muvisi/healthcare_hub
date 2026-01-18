# retail_members/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

# @shared_task
def send_test_email():
    subject = "Test Email from Hais Notifications"
    message = "This is a test email sent from Django using your configured SMTP server."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = ["mwangangimuvisi@gmail.com"]

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        print(f"Test email sent successfully to {recipient_list[0]}")
        return True
    except Exception as e:
        print("Failed to send test email:", e)
        return False



import logging
from celery import shared_task
from django.db import connections, transaction, DatabaseError
from smart.models import Benefit

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="benefit_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)






# @shared_task(name="smart.benefits.fetch_unsynced_benefits_task")
# def fetch_unsynced_benefits_task():
#     logger.info("[TASK] fetch_unsynced_benefits started...")

#     query = """
#         SELECT 
#             c.*, 
#             g.*, 
#             ca.*, 
#             b.*
#         FROM corporate c
#         INNER JOIN corp_groups g
#             ON c.CORP_ID = g.CORP_ID
#         INNER JOIN corp_anniversary ca
#             ON c.CORP_ID = ca.CORP_ID
#         INNER JOIN benefit b
#             ON g.benefit = b.code
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

#     saved = 0

#     with transaction.atomic():
#         for row in rows:
#             x = dict(zip(columns, row))

#             obj, created = Benefit.objects.update_or_create(
#                 idx=x["idx"],
#                 defaults={
#                     "CatCode": x["category"],
#                     "clnBenCode": x["code"],
#                     "clnPolCode": x["policy_no"],
#                     "benTypeId": x["sharing"],
#                     "subLimitAmt": x["limit"],
#                     "serviceType": x["code"],
#                     "benefitDesc": x["benefit"],
#                     "benLinked2Tqcode": x.get("sub_benefit"),
#                     "memAssignedBenefit": x.get("class"),
#                     "userId": x["USER_ID"],
#                     "synced": False
#                 }
#             )

#             saved += 1

#     logger.info(f"[fetch_unsynced_benefits] Saved {saved} benefits")
#     return {"status": "success", "saved": saved}
