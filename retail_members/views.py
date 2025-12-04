from django.shortcuts import render

# Create your views here.
# views.py
from django.http import JsonResponse
from django.db import connections, DatabaseError

from retail_members.sync_members import sync_all_members

def remote_users_api(request):
    """
    Fetch all users directly from the remote SQL Server DB
    and return them as JSON.
    """
    users_list = []
    try:
        with connections['external_mssql'].cursor() as cursor:
            cursor.execute("SELECT * FROM users")  # replace 'users' with your remote table
            columns = [col[0] for col in cursor.description]  # get column names
            for row in cursor.fetchall():
                users_list.append(dict(zip(columns, row)))
    except DatabaseError as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(users_list, safe=False)
# views.py
from django.http import JsonResponse
from rest_framework.decorators import api_view
# from .utils.smart_sync import sync_all_members

# @api_view(['GET'])
# def sync_members_api(request):
#     """
#     API endpoint to sync members from HAIS to Smart.
#     Call this endpoint to execute the sync.
#     """
#     result = sync_all_members()
#     return JsonResponse(result)

# views.py
from django.http import JsonResponse
# from .utils.smart_sync import sync_all_members

def sync_members_api(request):
    """
    Call this API to execute the member sync
    """
    if request.method == "GET":
        result = sync_all_members()
        return JsonResponse(result)
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
