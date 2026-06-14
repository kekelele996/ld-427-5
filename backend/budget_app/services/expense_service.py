from datetime import date

from django.db import transaction
from rest_framework.exceptions import ValidationError

from budget_app.models import AuditLog, ExpenseRecord, ExpenseStatus, SupplierStatus
from budget_app.services.balance_calculator import BalanceCalculator


class ExpenseService:
    def __init__(self) -> None:
        self.calculator = BalanceCalculator()

    @staticmethod
    def _validate_supplier_status(expense: ExpenseRecord) -> None:
        supplier = expense.supplier
        if supplier.status == SupplierStatus.BLACKLISTED:
            raise ValidationError(f"该供应商「{supplier.name}」已被加入黑名单，无法继续操作。")
        if supplier.status == SupplierStatus.SUSPENDED:
            raise ValidationError(f"与供应商「{supplier.name}」的合作已暂停，无法继续操作。")

    @transaction.atomic
    def submit(self, expense: ExpenseRecord, actor_id: str) -> ExpenseRecord:
        if expense.status != ExpenseStatus.DRAFT:
            raise ValidationError("只有草稿支出可以提交审批。")
        self._validate_supplier_status(expense)
        return self._transition(expense, ExpenseStatus.SUBMITTED, actor_id, "expense.submit")

    @transaction.atomic
    def approve(self, expense: ExpenseRecord, actor_id: str, comment: str = "") -> ExpenseRecord:
        if expense.status != ExpenseStatus.SUBMITTED:
            raise ValidationError("只有已提交支出可以审批。")
        self._validate_supplier_status(expense)
        expense.approver_id = actor_id
        expense.approval_comment = comment
        updated = self._transition(expense, ExpenseStatus.APPROVED, actor_id, "expense.approve")
        self.calculator.recalculate_item(updated.budget_item)
        self.calculator.recalculate_sheet(updated.budget_item.budget_sheet)
        return updated

    @transaction.atomic
    def pay(self, expense: ExpenseRecord, actor_id: str) -> ExpenseRecord:
        if expense.status != ExpenseStatus.APPROVED:
            raise ValidationError("只有已审批支出可以确认付款。")
        self._validate_supplier_status(expense)
        expense.paid_at = date.today()
        return self._transition(expense, ExpenseStatus.PAID, actor_id, "expense.pay")

    def _transition(self, expense: ExpenseRecord, status: str, actor_id: str, action: str) -> ExpenseRecord:
        before = {"status": expense.status}
        expense.status = status
        expense.save()
        self.calculator.recalculate_sheet(expense.budget_item.budget_sheet)
        AuditLog.objects.create(
            actor_id=actor_id,
            action=action,
            entity_type="ExpenseRecord",
            entity_id=str(expense.id),
            before=before,
            after={"status": expense.status},
        )
        return expense
