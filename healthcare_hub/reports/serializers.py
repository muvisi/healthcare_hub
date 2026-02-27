# report/serializers.py
from rest_framework import serializers
from engine.models import (
    ProviderRestrictionSyncFailure,
    ProviderRestrictionSyncSuccess,
    WaitingPeriodSyncFailure,
    WaitingPeriodSyncSuccess,
    HaisCategorySyncFailure,
    HaisCategorySyncSuccess,
    BenefitSyncFailure,
    BenefitSyncSuccess,
    MemberSyncFailure,
    MemberSyncSuccess,
    ApiSyncLog,
    CopayLog,
)

class ProviderRestrictionSyncFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderRestrictionSyncFailure
        fields = '__all__'

class ProviderRestrictionSyncSuccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderRestrictionSyncSuccess
        fields = '__all__'

class WaitingPeriodSyncFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitingPeriodSyncFailure
        fields = '__all__'

class WaitingPeriodSyncSuccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitingPeriodSyncSuccess
        fields = '__all__'

class HaisCategorySyncFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = HaisCategorySyncFailure
        fields = '__all__'

class HaisCategorySyncSuccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = HaisCategorySyncSuccess
        fields = '__all__'

class BenefitSyncFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenefitSyncFailure
        fields = '__all__'

class BenefitSyncSuccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenefitSyncSuccess
        fields = '__all__'

class MemberSyncFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberSyncFailure
        fields = '__all__'

class MemberSyncSuccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberSyncSuccess
        fields = '__all__'

class ApiSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiSyncLog
        fields = '__all__'

class CopayLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CopayLog
        fields = '__all__'
