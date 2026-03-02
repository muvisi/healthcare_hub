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