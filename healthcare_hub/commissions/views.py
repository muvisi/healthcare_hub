from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connections

# Create your views here.

class CommissionRecordsView(APIView):
    """ Returns commission records from the default_betterlife database using raw SQL. """
    def get(self, request):
        query = """
            SELECT DISTINCT ON (p.pushnotecode, p.customerscode)
                p.pushnotecode                AS push_note_code,
                p.pushnotecommission          AS commission_amount,
                p.pushnotedrcrnotenumber      AS dr_cr_note_number,
                p.pushnotepolicynumber        AS policy_number,
                t.transactionsnumber          AS transaction_number,
                p.pushnoteagentcode           AS agent_code,
                p.customerscode               AS customer_code,
                t.transactionstotalamount     AS transaction_total_amount,
                i.intermediaryname            AS intermediary_name,
                c.customerspolicyagentbrokername AS broker_name
            FROM pushnote p
            LEFT JOIN transactions t
                ON p.pushnotecode = t.transactionsnumber
            JOIN intermediary i
                ON p.pushnoteagentcode = i.intermediarycode
            JOIN customerspolicy c
                ON p.customerscode = c.customerscode
            ORDER BY
                p.pushnotecode,
                p.customerscode;
        """

        try:
            with connections['default_betterlife'].cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

            return Response({"success": True, "data": results}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
