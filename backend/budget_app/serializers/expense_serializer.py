from rest_framework import serializers

from budget_app.models import ExpenseRecord, ExpenseStatus, SupplierStatus


class ExpenseRecordSerializer(serializers.ModelSerializer):
    def validate_supplier(self, value):
        if self.instance and self.instance.status in (ExpenseStatus.APPROVED, ExpenseStatus.PAID):
            return value
        if value.status == SupplierStatus.BLACKLISTED:
            raise serializers.ValidationError("该供应商已被加入黑名单，无法选用。")
        if value.status == SupplierStatus.SUSPENDED:
            raise serializers.ValidationError("与该供应商的合作已暂停，无法选用。")
        return value

    class Meta:
        model = ExpenseRecord
        fields = [
            "id",
            "budget_item",
            "amount",
            "expense_date",
            "payment_method",
            "supplier",
            "invoice_no",
            "description",
            "attachment_url",
            "status",
            "applicant_id",
            "approver_id",
            "approval_comment",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["approver_id", "approval_comment", "paid_at", "created_at", "updated_at"]
