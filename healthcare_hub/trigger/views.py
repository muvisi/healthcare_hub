# # triggers/views.py
# from django.db import connections, transaction
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status, permissions

# from trigger.serializer import TriggerLogSerializer
# from .models import TriggerLog
# # from .serializers import TriggerLogSerializer

# class TriggerSectionAPIView(APIView):
#     """
#     Trigger action for a section:
#     1️⃣ Save locally in TriggerLog
#     2️⃣ Update sync column to NULL in remote MSSQL
#     """
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, *args, **kwargs):
#         section = request.data.get("section")
#         member_no = request.data.get("memberNo")
#         username = request.user.username if request.user else None

#         if not section or not member_no:
#             return Response(
#                 {"error": "Section and member_no are required."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # ---------- Save log locally ----------
#         trigger_log = TriggerLog.objects.create(
#             section=section, member_no=member_no, triggered_by=username
#         )
#         serializer = TriggerLogSerializer(trigger_log)

#         # ---------- Update remote MSSQL ----------
#         try:
#             with connections['external_mssql'].cursor() as cursor:
#                 with transaction.atomic(using='external_mssql'):
#                     # 1️⃣ principal_applicant
#                     cursor.execute(
#                         "UPDATE principal_applicant SET sync = NULL WHERE family_no = (SELECT family_no FROM member_info WHERE member_no = %s)",
#                         [member_no]
#                     )

#                     # 2️⃣ member_info
#                     cursor.execute(
#                         "UPDATE member_info SET sync = NULL WHERE member_no = %s",
#                         [member_no]
#                     )

#                     # 3️⃣ member_anniversary
#                     cursor.execute(
#                         """
#                         UPDATE member_anniversary
#                         SET sync = NULL
#                         WHERE member_no = %s
#                         AND GETDATE() BETWEEN start_date AND end_date
#                         """,
#                         [member_no]
#                     )

#                     # 4️⃣ member_benefits
#                     cursor.execute(
#                         """
#                         UPDATE member_benefits
#                         SET sync = NULL
#                         WHERE member_no = %s
#                         AND anniv = (
#                             SELECT anniv 
#                             FROM member_anniversary 
#                             WHERE member_no = member_benefits.member_no
#                               AND GETDATE() BETWEEN start_date AND end_date
#                         )
#                         """,
#                         [member_no]
#                     )

#         except Exception as e:
#             return Response(
#                 {"error": f"Failed to update remote DB: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         return Response(
#             {
#                 "message": f"Triggered {section} for {member_no}",
#                 "data": serializer.data,
#             },
#             status=status.HTTP_200_OK,
#         )


# triggers/views.py
from django.db import connections, transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from datetime import datetime

from .models import TriggerLog
from .serializer import TriggerLogSerializer


class TriggerSectionAPIView(APIView):
    """
    Trigger action for a section:
    1️⃣ Save locally in TriggerLog
    2️⃣ Update sync column to NULL in remote MSSQL based on section
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        section = request.data.get("section")
        member_no = request.data.get("memberNo")
        corp_id = request.data.get("corp_id")  # for corporate sections
        username = request.user.username if request.user else None

        if not section:
            return Response(
                {"error": "Section is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------- Save log locally ----------
        trigger_log = TriggerLog.objects.create(
            section=section,
            member_no=member_no or corp_id,
            triggered_by=username,
        )
        serializer = TriggerLogSerializer(trigger_log)

        try:
            with connections['external_mssql'].cursor() as cursor:
                with transaction.atomic(using='external_mssql'):
                    # ---------- MEMBER SECTIONS ----------
                    if section.lower() in ["members", "benefits", "categories", "copays", "waiting periods", "restrictions"]:
                        if not member_no:
                            return Response(
                                {"error": "memberNo is required for member sections."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        # principal_applicant
                        cursor.execute(
                            """
                            UPDATE principal_applicant
                            SET sync = NULL
                            WHERE family_no = (SELECT family_no FROM member_info WHERE member_no = %s)
                            """,
                            [member_no]
                        )

                        # member_info
                        cursor.execute(
                            "UPDATE member_info SET sync = NULL WHERE member_no = %s",
                            [member_no]
                        )

                        # member_anniversary
                        cursor.execute(
                            """
                            UPDATE member_anniversary
                            SET sync = NULL
                            WHERE member_no = %s
                              AND GETDATE() BETWEEN start_date AND end_date
                            """,
                            [member_no]
                        )

                        # member_benefits
                        cursor.execute(
                            """
                            UPDATE member_benefits
                            SET sync = NULL
                            WHERE member_no = %s
                              AND anniv = (
                                  SELECT anniv
                                  FROM member_anniversary
                                  WHERE member_no = member_benefits.member_no
                                    AND GETDATE() BETWEEN start_date AND end_date
                              )
                            """,
                            [member_no]
                        )

                    # ---------- CORPORATE SECTIONS ----------
                    elif section.lower() in ["corporate", "corp_groups", "corp_anniversary"]:
                        if not corp_id:
                            return Response(
                                {"error": "corp_id is required for corporate sections."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        # 1️⃣ Get current anniversary
                        cursor.execute(
                            """
                            SELECT anniv
                            FROM corp_anniversary
                            WHERE corp_id = %s
                              AND GETDATE() BETWEEN start_date AND end_date
                            """,
                            [corp_id]
                        )
                        anniv_row = cursor.fetchone()
                        anniv = anniv_row[0] if anniv_row else None

                        # 2️⃣ Update corp_groups
                        if anniv:
                            cursor.execute(
                                """
                                UPDATE corp_groups
                                SET sync = NULL
                                WHERE corp_id = %s AND anniv = %s
                                """,
                                [corp_id, anniv]
                            )

                        # 3️⃣ Update corporate
                        cursor.execute(
                            "UPDATE corporate SET sync = NULL WHERE corp_id = %s",
                            [corp_id]
                        )

                        # 4️⃣ Update corp_anniversary
                        cursor.execute(
                            """
                            UPDATE corp_anniversary
                            SET sync = NULL
                            WHERE corp_id = %s
                              AND GETDATE() BETWEEN start_date AND end_date
                            """,
                            [corp_id]
                        )

                    else:
                        return Response(
                            {"error": f"Unknown section: {section}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

        except Exception as e:
            return Response(
                {"error": f"Failed to update remote DB: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": f"Triggered {section} for {member_no or corp_id}",
                "anniv_used": anniv if section.lower() in ["corporate", "corp_groups", "corp_anniversary"] else None,
                "log": serializer.data,
            },
            status=status.HTTP_200_OK,
        )