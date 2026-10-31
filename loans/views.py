import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from .models import Customer, LoanType, LoanApplication, Repayment, LoanApproval
from .forms import CustomerRegistrationForm, CustomerProfileForm, LoanApplicationForm, RepaymentForm
from .utils import (
    calculate_credit_score,
    evaluate_risk_and_decision,
    calculate_emi,
    classify_delinquency,
    generate_repayment_schedule,
    generate_otp,
    build_whatsapp_url,
    verify_bvn_number,
    send_multichannel_alert
)

def is_manager(user):
    """Checks whether the logged-in user is a staff member or admin/manager."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ==============================================================================
# 1. VISITOR & AUTHENTICATION VIEWS
# ==============================================================================

def landing_page(request):
    """Visitor landing page displaying cooperative loan types and JS calculator."""
    loan_types = LoanType.objects.all()
    return render(request, 'loans/landing.html', {'loan_types': loan_types})


def register_view(request):
    """
    Registers a new member, generates an OTP, and sends automated 
    WhatsApp verification code via Ultramsg directly to the member's phone.
    """
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            phone = form.cleaned_data['phone']
            otp = generate_otp()
            Customer.objects.create(
                user=user,
                phone=phone,
                otp_code=otp,
                phone_verified=False
            )

            # Automatically log in the newly registered member
            login(request, user)

            # Automated WhatsApp OTP Dispatch via Ultramsg
            otp_msg = (
                f"🏦 *FEDPOD COOPERATIVE*\n\n"
                f"Welcome, {user.first_name}!\n"
                f"Your phone verification code is:\n\n"
                f"👉 *{otp}*\n\n"
                f"Enter this 6-digit code on your profile to verify your account."
            )
            ok, status_msg = send_multichannel_alert(phone, otp_msg)
            if ok:
                messages.success(request, f"Account created! Verification code sent to your WhatsApp ({phone}).")
            else:
                messages.info(request, f"Account created! Please verify your phone number. ({status_msg})")

            return redirect('verify_phone')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'loans/register.html', {'form': form})


def login_view(request):
    """Handles login for Customers, Managers, and Superusers."""
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        uname = request.POST.get('username')
        pword = request.POST.get('password')
        user = authenticate(request, username=uname, password=pword)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'loans/login.html')


def logout_view(request):
    """Safely logs out the active session."""
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('landing')


@login_required
def dashboard_redirect(request):
    """Routes managers to manager portal and members to customer dashboard."""
    if is_manager(request.user):
        return redirect('manager_dashboard')
    return redirect('customer_dashboard')


# ==============================================================================
# 2. CUSTOMER DASHBOARD, PROFILE, OTP & BVN VERIFICATION VIEWS
# ==============================================================================

@login_required
def customer_dashboard(request):
    """Customer Dashboard showing running loans, KYC completion, and repayment dues."""
    customer, _ = Customer.objects.get_or_create(user=request.user)
    my_loans = LoanApplication.objects.filter(customer=customer)

    unpaid_installments = Repayment.objects.filter(
        loan__customer=customer,
        loan__status='Disbursed',
        is_paid=False
    )

    total_debt = sum(rep.loan.emi_amount for rep in unpaid_installments)
    next_repayment = unpaid_installments.order_by('due_date').first()

    context = {
        'customer': customer,
        'my_loans': my_loans,
        'total_debt': round(total_debt, 2),
        'next_due_date': next_repayment.due_date if next_repayment else None,
        'next_due_amount': next_repayment.loan.emi_amount if next_repayment else 0,
        'next_repayment': next_repayment,
    }
    return render(request, 'loans/customer_dashboard.html', context)


@login_required
def complete_profile(request):
    """Handles KYC profile data, picture uploads, and resets verification if phone/BVN changes."""
    customer, _ = Customer.objects.get_or_create(user=request.user)
    old_phone = customer.phone
    old_bvn = customer.bvn

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            updated_customer = form.save(commit=False)

            if updated_customer.phone != old_phone:
                updated_customer.phone_verified = False
                updated_customer.otp_code = generate_otp()

            if updated_customer.bvn != old_bvn:
                updated_customer.bvn_verified = False

            updated_customer.save()
            messages.success(request, "Profile updated successfully! Now complete Phone and BVN verification.")
            return redirect('complete_profile')
    else:
        form = CustomerProfileForm(instance=customer)

    return render(request, 'loans/profile_form.html', {'form': form, 'customer': customer})


@login_required
def send_or_verify_phone_otp(request):
    """Verifies phone ownership using 6-digit OTP dispatched via Ultramsg."""
    customer, _ = Customer.objects.get_or_create(user=request.user)

    if not customer.phone:
        messages.warning(request, "Please enter your phone number first.")
        return redirect('complete_profile')

    if not customer.otp_code:
        customer.otp_code = generate_otp()
        customer.save()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'resend':
            customer.otp_code = generate_otp()
            customer.save()
            otp_msg = (
                f"🏦 *FEDPOD COOPERATIVE*\n\n"
                f"Your new phone verification code is:\n\n"
                f"👉 *{customer.otp_code}*"
            )
            ok, status_msg = send_multichannel_alert(customer.phone, otp_msg)
            if ok:
                messages.success(request, f"New OTP sent to your WhatsApp ({customer.phone})!")
            else:
                messages.info(request, f"OTP generated! ({status_msg})")
            return redirect('verify_phone')

        elif action == 'verify':
            entered_otp = request.POST.get('otp_code', '').strip()
            if entered_otp == customer.otp_code:
                customer.phone_verified = True
                customer.otp_code = ''
                customer.save()
                messages.success(request, f"Phone number ({customer.phone}) verified successfully!")
                return redirect('complete_profile')
            else:
                messages.error(request, "Incorrect OTP code entered. Please check and try again.")

    wa_msg = f"FEDPOD Cooperative Phone Verification Code: *{customer.otp_code}*"
    whatsapp_otp_url = build_whatsapp_url(customer.phone, wa_msg)

    return render(request, 'loans/verify_phone.html', {
        'customer': customer,
        'whatsapp_otp_url': whatsapp_otp_url
    })


@login_required
def verify_bvn_action(request):
    """Validates 11-digit BVN structure and uniqueness."""
    customer, _ = Customer.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        bvn_to_check = request.POST.get('bvn', customer.bvn).strip()
        customer.bvn = bvn_to_check
        is_valid, msg = verify_bvn_number(bvn_to_check, customer, Customer)
        if is_valid:
            customer.bvn_verified = True
            customer.save()
            messages.success(request, msg)
        else:
            customer.bvn_verified = False
            customer.save()
            messages.error(request, msg)

    return redirect('complete_profile')


# ==============================================================================
# 3. LOAN APPLICATION & SELF-SERVICE REPAYMENT VIEWS
# ==============================================================================

@login_required
def apply_loan(request):
    """
    Submits loan application, evaluates credit score, and blocks duplicate running loans.
    """
    customer, _ = Customer.objects.get_or_create(user=request.user)

    # 1. Enforce 100% KYC completion
    if not customer.is_profile_complete():
        messages.warning(
            request,
            "Please complete 100% of your profile (including Phone OTP & BVN Verification) before applying."
        )
        return redirect('complete_profile')

    # 2. Strict Active Loan Rule (Blocks application if customer has an unpaid loan)
    if customer.has_active_loan():
        messages.error(
            request,
            "Application Blocked: You have an existing active loan that has not been completely paid off. Cooperative policy allows only one active loan at a time."
        )
        return redirect('customer_dashboard')

    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.customer = customer

            # Mathematical Credit Scoring
            score = calculate_credit_score(
                monthly_income=customer.monthly_income,
                monthly_expenses=customer.monthly_expenses,
                amount_requested=loan.amount_requested
            )

            # Automated Risk Level & Decision
            risk_level, status = evaluate_risk_and_decision(
                score=score,
                monthly_income=customer.monthly_income
            )

            # Equated Monthly Installment (EMI) Formula
            emi = calculate_emi(
                principal=loan.amount_requested,
                annual_rate=loan.loan_type.interest_rate,
                duration_months=loan.duration_months
            )

            loan.credit_score = score
            loan.risk_level = risk_level
            loan.status = status
            loan.emi_amount = emi
            loan.save()

            if status in ['Approved', 'Rejected']:
                LoanApproval.objects.create(
                    loan=loan,
                    approved_by=None,
                    remarks=f"Automated Credit Risk Evaluation Decision (Score: {score}, Risk: {risk_level})."
                )

            messages.success(request, f"{loan.loan_type.name} Loan application processed successfully!")
            return redirect('loan_result', loan_id=loan.id)
    else:
        form = LoanApplicationForm()

    loan_types = LoanType.objects.all()
    return render(request, 'loans/apply_loan.html', {
        'form': form,
        'customer': customer,
        'loan_types': loan_types
    })


@login_required
def loan_result(request, loan_id):
    """Displays credit evaluation results immediately after application."""
    loan = get_object_or_404(LoanApplication, id=loan_id)
    if loan.customer.user != request.user and not is_manager(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('customer_dashboard')
    return render(request, 'loans/loan_result.html', {'loan': loan})


@login_required
def loan_detail(request, loan_id):
    """Displays repayment schedule, payment modals, and management controls."""
    loan = get_object_or_404(LoanApplication, id=loan_id)
    if loan.customer.user != request.user and not is_manager(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('customer_dashboard')

    repayments = loan.repayments.all()
    approval = getattr(loan, 'approval_record', None)

    applicant_name = loan.customer.user.get_full_name() or loan.customer.user.username
    disburse_text = (
        f"Hello {applicant_name}, your FEDPOD Cooperative {loan.loan_type.name} Loan (#{loan.id}) "
        f"of N{loan.amount_requested:,} has been DISBURSED! Your monthly EMI is N{loan.emi_amount:,.2f} "
        f"for {loan.duration_months} months."
    )
    whatsapp_disburse_url = build_whatsapp_url(loan.customer.phone, disburse_text)

    repayment_list = []
    for rep in repayments:
        rem_text = (
            f"Hello {applicant_name}, reminder from FEDPOD Cooperative: "
            f"Your monthly EMI of N{loan.emi_amount:,.2f} for Loan #{loan.id} is due on {rep.due_date}."
        )
        rep.whatsapp_reminder_url = build_whatsapp_url(loan.customer.phone, rem_text)
        repayment_list.append(rep)

    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
        'repayments': repayment_list,
        'approval': approval,
        'is_manager': is_manager(request.user),
        'whatsapp_disburse_url': whatsapp_disburse_url,
    })


@login_required
def customer_pay_installment(request, repayment_id):
    """
    Self-service payment: Marks installment as paid and sends 
    an automated WhatsApp receipt via Ultramsg to the borrower.
    """
    repayment = get_object_or_404(Repayment, id=repayment_id)
    loan = repayment.loan

    if loan.customer.user != request.user and not is_manager(request.user):
        messages.error(request, "Unauthorized action.")
        return redirect('customer_dashboard')

    if request.method == 'POST' and not repayment.is_paid:
        payment_method = request.POST.get('payment_method', 'Card / Bank Transfer')
        ref = f"FP-{uuid.uuid4().hex[:8].upper()}"

        repayment.amount_paid = int(round(loan.emi_amount))
        repayment.payment_date = timezone.now().date()
        repayment.payment_reference = f"{ref} ({payment_method})"
        repayment.is_paid = True
        repayment.save()

        # Automated WhatsApp Payment Receipt via Ultramsg
        receipt_msg = (
            f"🧾 *FEDPOD COOPERATIVE - PAYMENT RECEIPT*\n\n"
            f"Dear {loan.customer.user.first_name},\n"
            f"Payment of *₦{repayment.amount_paid:,}* has been received for Loan #{loan.id} ({loan.loan_type.name} Loan).\n\n"
            f"• Channel: {payment_method}\n"
            f"• Transaction Ref: *{ref}*\n"
            f"• Date: {repayment.payment_date}\n\n"
            f"Thank you for keeping your loan account performing!"
        )
        send_multichannel_alert(loan.customer.phone, receipt_msg)

        messages.success(
            request,
            f"Payment of ₦{repayment.amount_paid:,} successful via {payment_method}! Ref: {ref}"
        )

    return redirect('loan_detail', loan_id=loan.id)


# ==============================================================================
# 4. LOAN MANAGER PORTAL & NOTIFICATIONS
# ==============================================================================

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    """Loan Manager Overview: Pending applications, delinquency classification, and quick actions."""
    all_loans = LoanApplication.objects.select_related('customer__user', 'loan_type').all()
    pending_loans = all_loans.filter(status='Pending')
    approved_loans = all_loans.filter(status='Approved')
    disbursed_loans = all_loans.filter(status='Disbursed')

    today = timezone.now().date()
    overdue_repayments_count = Repayment.objects.filter(is_paid=False, due_date__lt=today).count()

    delinquency_groups = {
        'Performing': [],
        'Watch': [],
        'Substandard': [],
        'Doubtful': [],
        'Loss': [],
    }

    for loan in disbursed_loans:
        unpaid = loan.repayments.filter(is_paid=False)
        max_overdue_days = 0
        for rep in unpaid:
            days = rep.days_overdue()
            if days > max_overdue_days:
                max_overdue_days = days

        category = classify_delinquency(max_overdue_days)
        borrower_name = loan.customer.user.get_full_name() or loan.customer.user.username
        wa_reminder = build_whatsapp_url(
            loan.customer.phone,
            f"Hello {borrower_name}, reminder from FEDPOD Cooperative: Your Loan #{loan.id} EMI of N{loan.emi_amount:,.2f} is due ({category} status)."
        )

        delinquency_groups[category].append({
            'loan': loan,
            'max_overdue_days': max_overdue_days,
            'category': category,
            'unpaid_count': unpaid.count(),
            'whatsapp_url': wa_reminder,
        })

    context = {
        'total_count': all_loans.count(),
        'pending_count': pending_loans.count(),
        'approved_count': all_loans.filter(status__in=['Approved', 'Disbursed']).count(),
        'overdue_count': overdue_repayments_count,
        'pending_loans': pending_loans,
        'approved_loans': approved_loans,
        'disbursed_loans': disbursed_loans,
        'delinquency_groups': delinquency_groups,
    }
    return render(request, 'loans/manager_dashboard.html', context)


@login_required
@user_passes_test(is_manager)
def process_loan_decision(request, loan_id):
    """
    Approves, Rejects, or Disburses a loan. 
    When Disbursed, generates the EMI schedule and sends automated WhatsApp notification via Ultramsg.
    """
    loan = get_object_or_404(LoanApplication, id=loan_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '').strip() or f"Processed as {action} by Loan Manager."

        if action in ['Approved', 'Rejected', 'Disbursed']:
            loan.status = action
            loan.save()

            LoanApproval.objects.update_or_create(
                loan=loan,
                defaults={
                    'approved_by': request.user,
                    'remarks': remarks
                }
            )

            applicant_name = loan.customer.user.get_full_name() or loan.customer.user.username

            if action == 'Disbursed':
                generate_repayment_schedule(loan, Repayment)
                first_rep = loan.repayments.first()
                first_due_str = str(first_rep.due_date) if first_rep else "in 30 days"

                # Automated WhatsApp Disbursement Notification via Ultramsg
                disbursement_msg = (
                    f"🎉 *FEDPOD COOPERATIVE - LOAN DISBURSED*\n\n"
                    f"Dear {applicant_name},\n"
                    f"Your *{loan.loan_type.name} Loan* (#{loan.id}) of *₦{loan.amount_requested:,}* has been approved and DISBURSED.\n\n"
                    f"• Duration: {loan.duration_months} Months\n"
                    f"• Monthly EMI: *₦{loan.emi_amount:,.2f}*\n"
                    f"• First Due Date: *{first_due_str}*\n\n"
                    f"Please log in to your dashboard to view your repayment schedule."
                )
                ok, status_msg = send_multichannel_alert(loan.customer.phone, disbursement_msg)

                messages.success(
                    request,
                    f"Loan #{loan.id} DISBURSED! {loan.duration_months} monthly installments generated and WhatsApp alert sent."
                )
            else:
                alert_text = (
                    f"📢 *FEDPOD COOPERATIVE*\n\n"
                    f"Dear {applicant_name}, your {loan.loan_type.name} Loan application (#{loan.id}) "
                    f"status has been updated to: *{action.upper()}*."
                )
                send_multichannel_alert(loan.customer.phone, alert_text)
                messages.success(request, f"Loan #{loan.id} status updated to {action}.")

    return redirect('loan_detail', loan_id=loan.id)


@login_required
@user_passes_test(is_manager)
def send_due_sms_reminder(request, repayment_id):
    """Triggers an instant automated WhatsApp reminder to a borrower."""
    rep = get_object_or_404(Repayment, id=repayment_id)
    loan = rep.loan
    name = loan.customer.user.get_full_name() or loan.customer.user.username

    msg = (
        f"⏰ *FEDPOD COOPERATIVE - DUE REMINDER*\n\n"
        f"Dear {name},\n"
        f"Your monthly EMI installment of *₦{loan.emi_amount:,.2f}* for Loan #{loan.id} "
        f"is due on *{rep.due_date}*.\n\n"
        f"Please log in to your dashboard to make your repayment."
    )
    ok, status_msg = send_multichannel_alert(loan.customer.phone, msg)
    if ok:
        messages.success(request, f"Automated WhatsApp reminder sent to {loan.customer.phone}!")
    else:
        messages.warning(request, f"Notification status: {status_msg}")

    return redirect('loan_detail', loan_id=loan.id)


@login_required
@user_passes_test(is_manager)
def record_repayment(request, repayment_id):
    """Manual repayment recording by the Loan Manager."""
    repayment = get_object_or_404(Repayment, id=repayment_id)
    loan = repayment.loan

    if request.method == 'POST':
        form = RepaymentForm(request.POST, instance=repayment)
        if form.is_valid():
            rep = form.save(commit=False)
            if rep.is_paid and not rep.payment_date:
                rep.payment_date = timezone.now().date()
            if rep.is_paid and not rep.payment_reference:
                rep.payment_reference = f"MGR-{uuid.uuid4().hex[:6].upper()}"
            rep.save()

            receipt_msg = (
                f"🧾 *FEDPOD COOPERATIVE - PAYMENT RECORDED*\n\n"
                f"Payment of *₦{rep.amount_paid:,}* recorded for Loan #{loan.id} (Due Date: {rep.due_date}).\n"
                f"Status: PAID ✓\n\n"
                f"Thank you!"
            )
            send_multichannel_alert(loan.customer.phone, receipt_msg)

            messages.success(request, f"Repayment for Loan #{loan.id} recorded and WhatsApp receipt sent!")
            return redirect('loan_detail', loan_id=loan.id)
    else:
        initial_data = {
            'amount_paid': int(round(loan.emi_amount)),
            'payment_date': timezone.now().date(),
            'is_paid': True
        }
        form = RepaymentForm(instance=repayment, initial=initial_data)

    return render(request, 'loans/record_repayment.html', {
        'form': form,
        'repayment': repayment,
        'loan': loan
    })


@login_required
@user_passes_test(is_manager)
def reports_view(request):
    """Print-friendly executive report summarizing total disbursements, collections, and defaults."""
    disbursed_loans = LoanApplication.objects.filter(status='Disbursed')
    total_principal_disbursed = disbursed_loans.aggregate(total=Sum('amount_requested'))['total'] or 0
    total_expected_return = sum(loan.total_payable() for loan in disbursed_loans)
    total_recovered = Repayment.objects.filter(is_paid=True).aggregate(total=Sum('amount_paid'))['total'] or 0

    today = timezone.now().date()
    overdue_installments = Repayment.objects.filter(is_paid=False, due_date__lt=today).select_related('loan__customer__user')
    total_default_amount = sum(rep.loan.emi_amount for rep in overdue_installments)

    context = {
        'disbursed_loans': disbursed_loans,
        'total_principal_disbursed': total_principal_disbursed,
        'total_expected_return': round(total_expected_return, 2),
        'total_recovered': total_recovered,
        'total_default_amount': round(total_default_amount, 2),
        'overdue_installments': overdue_installments,
        'report_date': timezone.now(),
    }
    return render(request, 'loans/reports.html', context)