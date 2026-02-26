# trigger/serializers.py
from rest_framework import serializers
from .models import TriggerLog

class TriggerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerLog
        fields = "__all__"