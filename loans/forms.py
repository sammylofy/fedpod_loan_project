from django import forms
from django.contrib.auth.models import User
from .models import Customer, LoanApplication, Repayment

class CustomerRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter First Name'})
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Surname'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'staff@fedpod.edu.ng'})
    )
    phone = forms.CharField(
        max_length=15, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 08031234567'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create Password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose Staff/Member Username'}),
        }

    def clean_phone(self):
        phone = ''.join(filter(str.isdigit, self.cleaned_data.get('phone', '')))
        if len(phone) < 10 or len(phone) > 14:
            raise forms.ValidationError("Enter a valid Nigerian phone number (e.g. 08031234567).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")
        return cleaned_data


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['profile_picture', 'phone', 'address', 'monthly_income', 'monthly_expenses', 'employment_status', 'bvn']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 08031234567'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Residential or Department Address'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'form-control', 'min': '10000'}),
            'monthly_expenses': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'bvn': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11', 'placeholder': '11-digit BVN starting with 22...'}),
        }

    def clean_bvn(self):
        bvn = self.cleaned_data.get('bvn', '').strip()
        if not bvn.isdigit() or len(bvn) != 11:
            raise forms.ValidationError("BVN must be exactly 11 digits.")
        return bvn


class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = ['loan_type', 'amount_requested', 'duration_months', 'purpose']
        widgets = {
            'loan_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_loan_type'}),
            'amount_requested': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_amount_requested', 'min': '5000', 'placeholder': 'Amount in Naira (₦)'}),
            'duration_months': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_duration_months', 'min': '1', 'placeholder': 'Repayment duration in months'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explain the purpose of this cooperative loan...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['loan_type'].empty_label = "-- Select a Cooperative Loan Category --"

    def clean(self):
        cleaned_data = super().clean()
        loan_type = cleaned_data.get('loan_type')
        amount = cleaned_data.get('amount_requested')
        duration = cleaned_data.get('duration_months')

        if not loan_type:
            self.add_error('loan_type', "Please select a valid Loan Type.")
            return cleaned_data

        if amount is not None:
            if amount > loan_type.max_amount:
                self.add_error(
                    'amount_requested',
                    f"Limit Exceeded! {loan_type.name} Loan allows a maximum of ₦{loan_type.max_amount:,} (You entered ₦{amount:,})."
                )
            elif amount < 5000:
                self.add_error('amount_requested', "Minimum loan request is ₦5,000.")

        if duration is not None:
            if duration > loan_type.max_duration_months:
                self.add_error(
                    'duration_months',
                    f"Duration Exceeded! {loan_type.name} Loan allows a maximum tenure of {loan_type.max_duration_months} months (You entered {duration} months)."
                )
            elif duration < 1:
                self.add_error('duration_months', "Duration must be at least 1 month.")

        return cleaned_data


class RepaymentForm(forms.ModelForm):
    class Meta:
        model = Repayment
        fields = ['amount_paid', 'payment_date', 'is_paid']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }