from django.contrib import admin
from .models import Customer, LoanType, LoanApplication, Repayment, LoanApproval

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'phone_verified', 'employment_status', 'monthly_income', 'bvn', 'bvn_verified', 'date_joined')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone', 'bvn')
    list_filter = ('phone_verified', 'bvn_verified', 'employment_status')

@admin.register(LoanType)
class LoanTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'interest_rate', 'max_amount', 'max_duration_months')

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'loan_type', 'amount_requested', 'duration_months', 'credit_score', 'risk_level', 'emi_amount', 'status', 'application_date')
    list_filter = ('status', 'risk_level', 'loan_type')
    search_fields = ('customer__user__username', 'customer__user__first_name', 'purpose')

@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan', 'due_date', 'amount_paid', 'payment_date', 'payment_reference', 'is_paid', 'days_overdue')
    list_filter = ('is_paid', 'due_date')

@admin.register(LoanApproval)
class LoanApprovalAdmin(admin.ModelAdmin):
    list_display = ('loan', 'approved_by', 'approval_date', 'remarks')
    list_filter = ('approval_date',)