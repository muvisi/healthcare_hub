# from rest_framework import viewsets
# from .models import Users
# from .serializers import UsersSerializer

# class UsersViewSet(viewsets.ModelViewSet):
#     queryset = Users.objects.all()
#     serializer_class = UsersSerializer

from rest_framework import serializers
from .models import Users

class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['uuid', 'username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True}  # Hide password in responses
        }
        
# from rest_framework import serializers
# from django.contrib.auth.hashers import check_password
# from .models import Users

# class LoginSerializer(serializers.Serializer):
#     username = serializers.CharField()
#     password = serializers.CharField(write_only=True)

#     def validate(self, data):
#         username = data.get('username')
#         password = data.get('password')

#         try:
#             user = Users.objects.get(username=username)
#         except Users.DoesNotExist:
#             raise serializers.ValidationError("Invalid username or password")

#         if not check_password(password, user.password):
#             raise serializers.ValidationError("Invalid username or password")

#         data['user'] = user
#         return data

from rest_framework import serializers
from django.contrib.auth.hashers import check_password
from .models import Users

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        # Check username
        try:
            user = Users.objects.get(username=username)
        except Users.DoesNotExist:
            raise serializers.ValidationError({
                "username": "Username does not exist"
            })

        # Check password
        if not check_password(password, user.password):
            raise serializers.ValidationError({
                "password": "Incorrect password"
            })

        data["user"] = user
        return data

from django.conf import settings
import ldap3
from ldap3.core.exceptions import LDAPException

class LDAPLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        # 1. Check if user exists in the local database and is active
        try:
            user = Users.objects.get(username=username)
        except Users.DoesNotExist:
            raise serializers.ValidationError({
                "username": "Username does not exist or unauthorized."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "username": "User account is inactive."
            })

        # 2. Attempt LDAP Bind
        ldap_server_url = settings.LDAP_SERVER_URL
        ldap_domain = settings.LDAP_DOMAIN

        # Typically AD format is DOMAIN\username or username@domain.com
        # Adjusting login format as DOMAIN\username:
        ldap_user = f"{ldap_domain}\\{username}" if "\\" not in ldap_domain else f"{ldap_domain}\\{username}"
        # If the domain is used differently, adjust the string formatting here.
        # Alternatively, for e.g. user@domain.com: ldap_user = f"{username}@{ldap_domain}"

        try:
            server = ldap3.Server(ldap_server_url, get_info=ldap3.ALL)
            conn = ldap3.Connection(server, user=ldap_user, password=password, auto_bind=True)
            # If auto_bind=True doesn't raise an exception, authentication is successful.
            conn.unbind()
        except LDAPException:
            raise serializers.ValidationError({
                "password": "LDAP authentication failed. Incorrect password."
            })

        data["user"] = user
        return data
