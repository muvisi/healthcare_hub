import decimal
from rest_framework import serializers

class CommissionRecordSerializer(serializers.Serializer):
    push_note_code = serializers.CharField(allow_null=True, required=False)
    commission_amount = serializers.SerializerMethodField()
    dr_cr_note_number = serializers.CharField(allow_null=True, required=False)
    policy_number = serializers.CharField(allow_null=True, required=False)
    transaction_number = serializers.CharField(allow_null=True, required=False)
    agent_code = serializers.CharField(allow_null=True, required=False)
    customer_code = serializers.CharField(allow_null=True, required=False)
    transaction_total_amount = serializers.SerializerMethodField()
    intermediary_name = serializers.CharField(allow_null=True, required=False)
    broker_name = serializers.CharField(allow_null=True, required=False)
    intermediary_commission_rate = serializers.SerializerMethodField()
    intermediary_with_holding_tax_rate = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """ Also safely trims trailing spaces from string fields (often an issue in legacy SQL Char fields) """
        rep = super().to_representation(instance)
        for key, value in rep.items():
            if isinstance(value, str):
                rep[key] = value.strip()
        return rep

    def get_commission_amount(self, obj):
        val = obj.get('commission_amount')
        if val is not None:
            try:
                return f"{decimal.Decimal(str(val)):,.2f}"
            except Exception:
                return val
        return val

    def get_transaction_total_amount(self, obj):
        val = obj.get('transaction_total_amount')
        if val is not None:
            try:
                return f"{decimal.Decimal(str(val)):,.2f}"
            except Exception:
                return val
        return val

    def get_intermediary_commission_rate(self, obj):
        val = obj.get('intermediary_commission_rate')
        if val is not None:
            try:
                d = decimal.Decimal(str(val)).normalize()
                return f"{d:f}%"  # :f translates to standard standard float notation without E
            except Exception:
                return val
        return val

    def get_intermediary_with_holding_tax_rate(self, obj):
        val = obj.get('intermediary_with_holding_tax_rate')
        if val is not None:
            try:
                d = decimal.Decimal(str(val)).normalize()
                return f"{d:f}%"
            except Exception:
                return val
        return val
