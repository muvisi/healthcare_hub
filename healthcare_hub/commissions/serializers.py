from rest_framework import serializers

class CommissionRecordSerializer(serializers.Serializer):
    push_note_code = serializers.CharField(allow_null=True, required=False)
    commission_amount = serializers.DecimalField(max_digits=20, decimal_places=2, allow_null=True, required=False)
    dr_cr_note_number = serializers.CharField(allow_null=True, required=False)
    policy_number = serializers.CharField(allow_null=True, required=False)
    transaction_number = serializers.CharField(allow_null=True, required=False)
    agent_code = serializers.CharField(allow_null=True, required=False)
    customer_code = serializers.CharField(allow_null=True, required=False)
    transaction_total_amount = serializers.DecimalField(max_digits=20, decimal_places=2, allow_null=True, required=False)
    intermediary_name = serializers.CharField(allow_null=True, required=False)
    broker_name = serializers.CharField(allow_null=True, required=False)

