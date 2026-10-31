from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 1. CUSTOMER MODEL (Upgraded with Profile Picture, Phone OTP & BVN Verification)
class Customer(models.Model):
    EMPLOYMENT_CHOICES = [
        ('Permanent Staff', 'Permanent Academic/Non-Academic Staff'),
        ('Contract Staff', 'Contract / Visiting Staff'),
        ('SME Owner', 'Cooperative Business Member'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    address = models.TextField(blank=True)
    monthly_income = models.IntegerField(default=0, help_text="Monthly Net Income in Naira (₦)")
    monthly_expenses = models.IntegerField(default=0, help_text="Monthly Total Expenses in Naira (₦)")
    employment_status = models.CharField(max_length=50, choices=EMPLOYMENT_CHOICES, blank=True)
    bvn = models.CharField(max_length=11, blank=True, help_text="11-digit Bank Verification Number")
    bvn_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.phone or 'No Phone'})"

    def profile_completion_percentage(self):
        """
        Calculates completion across 8 checkpoints:
        Phone, Phone Verified, Address, Income, Expenses, Employment, BVN, BVN Verified.
        """
        checks = [
            bool(self.phone),
            bool(self.phone_verified),
            bool(self.address),
            self.monthly_income > 0,
            self.monthly_expenses > 0,
            bool(self.employment_status),
            len(str(self.bvn)) == 11,
            bool(self.bvn_verified),
        ]
        completed = sum(1 for c in checks if c)
        return int((completed / len(checks)) * 100)

    def is_profile_complete(self):
        return self.profile_completion_percentage() == 100
    # In loans/models.py inside class Customer:

    def has_active_loan(self):
        """
        Returns True if the customer currently has:
        1. Any Disbursed loan that still has unpaid repayment installments, OR
        2. Any loan currently Pending or Approved awaiting disbursement.
        """
        # Check for running disbursed loans with outstanding installments
        has_unpaid_disbursed = self.loans.filter(
            status='Disbursed',
            repayments__is_paid=False
        ).exists()

        # Check for loans currently under review or awaiting disbursement
        has_pending_or_approved = self.loans.filter(
            status__in=['Pending', 'Approved']
        ).exists()

        return has_unpaid_disbursed or has_pending_or_approved

# 2. LOAN TYPE MODEL
class LoanType(models.Model):
    LOAN_NAME_CHOICES = [
        ('Personal', 'Personal Loan'),
        ('Gold', 'Gold / Emergency Loan'),
        ('Home', 'Home / Housing Loan'),
        ('Vehicle', 'Vehicle / Car Loan'),
        ('Business', 'Business / Agriculture Loan'),
    ]

    name = models.CharField(max_length=50, choices=LOAN_NAME_CHOICES, unique=True)
    interest_rate = models.FloatField(help_text="Annual Interest Rate (%)")
    max_amount = models.IntegerField(help_text="Maximum Loan Amount (₦)")
    max_duration_months = models.IntegerField(help_text="Maximum Duration (Months)")

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} Loan ({self.interest_rate}% p.a. - Max ₦{self.max_amount:,}, Max {self.max_duration_months}m)"


# 3. LOAN APPLICATION MODEL
class LoanApplication(models.Model):
    RISK_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Disbursed', 'Disbursed'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE, related_name='applications')
    amount_requested = models.IntegerField()
    duration_months = models.IntegerField()
    purpose = models.TextField()
    credit_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=15, choices=RISK_CHOICES, default='Medium')
    emi_amount = models.FloatField(default=0.0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    application_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-application_date']

    def __str__(self):
        return f"Loan #{self.id} - {self.customer.user.username} - ₦{self.amount_requested:,} ({self.status})"

    def total_payable(self):
        return round(self.emi_amount * self.duration_months, 2)


# 4. REPAYMENT MODEL
class Repayment(models.Model):
    loan = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='repayments')
    due_date = models.DateField()
    amount_paid = models.IntegerField(default=0)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=50, blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        status = "PAID" if self.is_paid else f"UNPAID (Due: {self.due_date})"
        return f"Loan #{self.loan.id} Installment - {status}"

    def days_overdue(self):
        if self.is_paid:
            return 0
        today = timezone.now().date()
        if today > self.due_date:
            return (today - self.due_date).days
        return 0


# 5. LOAN APPROVAL MODEL
class LoanApproval(models.Model):
    loan = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, related_name='approval_record')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    approval_date = models.DateTimeField(auto_now=True)
    remarks = models.TextField()

    def __str__(self):
        return f"Decision for Loan #{self.loan.id} by {self.approved_by}"