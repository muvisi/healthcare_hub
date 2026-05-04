from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connections
from rest_framework.pagination import PageNumberPagination
from .serializers import CommissionRecordSerializer

# Create your views here.

class CommissionRecordsView(APIView):
    """ Returns commission records from the default_betterlife database using raw SQL. """
    
    valid_filters = {
        'push_note_code': 'p.pushnotecode',
        'push_note_request_date': 'p.pushnotereqdatetime',
        'commission_amount': 'p.pushnotecommission',
        'dr_cr_note_number': 'p.pushnotedrcrnotenumber',
        'policy_number': 'p.pushnotepolicynumber',
        'transaction_number': 't.transactionsnumber',
        'agent_code': 'p.pushnoteagentcode',
        'customer_code': 'p.customerscode',
        'transaction_total_amount': 't.transactionstotalamount',
        'intermediary_name': 'i.intermediaryname',
        'broker_name': 'c.customerspolicyagentbrokername',
        'intermediary_commission_rate': 'i.intermediarycommisionrate',
        'intermediary_with_holding_tax_rate': 'i.intermediarywithholdingtax'
    }

    def get(self, request):
        where_clauses = []
        params = []

        # 1. Partial Match Filters ( mimicking filterset_fields with icontains )
        for param, col in self.valid_filters.items():
            val = request.query_params.get(param)
            if val:
                if param == 'push_note_request_date':
                    where_clauses.append("DATE(p.pushnotereqdatetime) = %s")
                    params.append(val)
                else:
                    where_clauses.append(f"{col}::text ILIKE %s")
                    params.append(f"%{val}%")

        # Handle explicit date range
        start_date = request.query_params.get('start_date')
        if start_date:
            where_clauses.append("DATE(p.pushnotereqdatetime) >= %s")
            params.append(start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            where_clauses.append("DATE(p.pushnotereqdatetime) <= %s")
            params.append(end_date)

        # 2. Global Search Filter ( applying to all fields )
        search = request.query_params.get('search')
        if search:
            search_cols = list(self.valid_filters.values())
            search_clause = " OR ".join([f"{col}::text ILIKE %s" for col in search_cols])
            where_clauses.append(f"({search_clause})")
            params.extend([f"%{search}%"] * len(search_cols))

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 3. Base Query
        # We wrap in a subquery so we can order the final results without violating DISTINCT ON constraints
        query = f"""
            SELECT * FROM (
                SELECT DISTINCT ON (p.pushnotecode, p.customerscode)
                    p.pushnotecode                AS push_note_code,
                    p.pushnotereqdatetime         AS push_note_request_date,
                    p.pushnotecommission          AS commission_amount,
                    p.pushnotedrcrnotenumber      AS dr_cr_note_number,
                    p.pushnotepolicynumber        AS policy_number,
                    t.transactionsnumber          AS transaction_number,
                    p.pushnoteagentcode           AS agent_code,
                    p.customerscode               AS customer_code,
                    t.transactionstotalamount     AS transaction_total_amount,
                    i.intermediaryname            AS intermediary_name,
                    c.customerspolicyagentbrokername AS broker_name,
                    i.intermediarycommisionrate           AS intermediary_commission_rate,
                    i.intermediarywithholdingtax            AS intermediary_with_holding_tax_rate
                FROM pushnote p
                LEFT JOIN transactions t
                    ON p.pushnotecode = t.transactionsnumber
                JOIN intermediary i
                    ON p.pushnoteagentcode = i.intermediarycode
                JOIN customerspolicy c
                    ON p.customerscode = c.customerscode
                {where_sql}
                ORDER BY
                    p.pushnotecode,
                    p.customerscode
            ) AS subquery
        """

        # 4. Ordering ( mimicking ordering parameters )
        outer_order = ""
        req_order = request.query_params.get('ordering')
        if req_order:
            desc = req_order.startswith('-')
            field = req_order.lstrip('-')
            if field in self.valid_filters:
                outer_order = f"ORDER BY {field} {'DESC' if desc else 'ASC'}"
        
        final_query = f"{query} {outer_order}"

        try:
            with connections['default_betterlife'].cursor() as cursor:
                cursor.execute(final_query, params)
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

            paginator = PageNumberPagination()
            paginated_results = paginator.paginate_queryset(results, request, view=self)
            
            serializer = CommissionRecordSerializer(paginated_results, many=True)
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
