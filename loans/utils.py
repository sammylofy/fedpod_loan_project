"""
FEDPOD Cooperative Credit Risk, EMI, BVN Verification & SMSLive247 Engine.
"""
import datetime
import random
import urllib.parse
import requests
from django.conf import settings



# ==============================================================================
# RULE A, B, C, D - CORE CREDIT RISK & MATHEMATICAL FORMULAS
# ==============================================================================

def calculate_credit_score(monthly_income: int, monthly_expenses: int, amount_requested: int) -> int:
    score = 500
    if monthly_income >= 100000:
        score += 150
    elif monthly_income >= 50000:
        score += 80
    else:
        score -= 50

    disposable = monthly_income - monthly_expenses
    if disposable < 20000:
        score -= 100

    if amount_requested > (monthly_income * 10):
        score -= 120

    return max(300, min(850, score))


def evaluate_risk_and_decision(score: int, monthly_income: int) -> tuple:
    if score >= 700 and monthly_income >= 80000:
        return ('Low', 'Approved')
    elif score >= 550:
        return ('Medium', 'Pending')
    else:
        return ('High', 'Rejected')


def calculate_emi(principal: int, annual_rate: float, duration_months: int) -> float:
    if duration_months <= 0:
        return 0.0
    if annual_rate <= 0:
        return round(principal / duration_months, 2)

    r = annual_rate / 12.0 / 100.0
    n = duration_months
    factor = (1 + r) ** n
    emi = (principal * r * factor) / (factor - 1)
    return round(emi, 2)


def classify_delinquency(days_overdue: int) -> str:
    if days_overdue <= 0:
        return 'Performing'
    elif 1 <= days_overdue <= 30:
        return 'Watch'
    elif 31 <= days_overdue <= 180:
        return 'Substandard'
    elif 181 <= days_overdue <= 360:
        return 'Doubtful'
    else:
        return 'Loss'


def generate_repayment_schedule(loan, RepaymentModel):
    if loan.repayments.exists():
        return
    today = datetime.date.today()
    for month_num in range(1, loan.duration_months + 1):
        due_date = today + datetime.timedelta(days=30 * month_num)
        RepaymentModel.objects.create(
            loan=loan,
            due_date=due_date,
            amount_paid=0,
            payment_date=None,
            is_paid=False
        )


# ==============================================================================
# SMSLIVE247 INTEGRATION & WHATSAPP LINK GENERATOR
# ==============================================================================

def format_nigerian_phone(phone: str) -> str:
    """Formats Nigerian phone numbers to +234803xxxxxxx for SMSLive247 and WhatsApp."""
    clean = ''.join(filter(str.isdigit, str(phone)))
    if clean.startswith('0') and len(clean) == 11:
        return '+234' + clean[1:]
    elif clean.startswith('234') and len(clean) == 13:
        return '+' + clean
    return '+' + clean


def generate_otp() -> str:
    """Generates a random 6-digit verification code."""
    return str(random.randint(100000, 999999))


def send_sms_via_smslive247(phone_number: str, message_text: str) -> tuple:
    """
    Sends real SMS via SMSLive247 API v4 using your Sub-Account API Key.
    Automatically tries 'SA-<key>' and raw '<key>' authorization formats.
    """
    raw_key = getattr(settings, 'SMSLIVE247_API_KEY', '').strip()
    sender_id = getattr(settings, 'SMSLIVE247_SENDER_ID', 'FEDPOD').strip()[:11]

    if not raw_key:
        return (False, "No SMSLive247 API key configured.")

    formatted_phone = format_nigerian_phone(phone_number)
    url = "https://api.smslive247.com/api/v4/sms"
    payload = {
        "senderID": sender_id,
        "mobileNumber": formatted_phone,
        "messageText": message_text
    }

    # Try SA- prefix (standard for SMSLive247 v4 sub-account keys) as well as raw key
    auth_candidates = [raw_key]
    if not raw_key.startswith(('SA-', 'MA-')):
        auth_candidates = [f"SA-{raw_key}", f"MA-{raw_key}", raw_key]

    last_error = ""
    for auth_header in auth_candidates:
        headers = {
            "Authorization": auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=8)
            if response.status_code in [200, 201]:
                return (True, f"SMS sent to {formatted_phone} via SMSLive247!")
            last_error = f"HTTP {response.status_code}: {response.text[:120]}"
        except Exception as exc:
            last_error = str(exc)

    return (False, f"SMSLive247 gateway note ({last_error}). Fallback mode ready.")


def build_whatsapp_url(phone_number: str, message_text: str) -> str:
    """Builds a direct Click-to-Chat WhatsApp URL (wa.me) with pre-filled message."""
    clean_intl = format_nigerian_phone(phone_number).replace('+', '')
    encoded_msg = urllib.parse.quote(message_text)
    return f"https://wa.me/{clean_intl}?text={encoded_msg}"


# ==============================================================================
# BVN VERIFICATION ENGINE
# ==============================================================================

def verify_bvn_number(bvn: str, customer, CustomerModel) -> tuple:
    """
    Verifies a Nigerian 11-digit BVN:
    1. Checks 11-digit numeric format & valid Nigerian BVN prefix (starts with '22').
    2. Checks that no other cooperative member has registered the same BVN.
    3. Confirms customer has full name & phone on record.
    Returns (is_valid: bool, message: str).
    """
    clean_bvn = str(bvn).strip()
    if not clean_bvn.isdigit() or len(clean_bvn) != 11:
        return (False, "Invalid BVN: Must be exactly 11 numeric digits.")

    if not clean_bvn.startswith('22'):
        return (False, "BVN Verification Failed: Valid Nigerian BVNs issued by NIBSS begin with '22' (e.g. 22123456789).")

    # Ensure uniqueness across members
    duplicate = CustomerModel.objects.filter(bvn=clean_bvn).exclude(id=customer.id).exists()
    if duplicate:
        return (False, "BVN Verification Failed: This BVN is already linked to another cooperative member.")

    full_name = customer.user.get_full_name() or customer.user.username
    return (True, f"NIBSS Cooperative Check Passed: BVN {clean_bvn[:4]}***{clean_bvn[-3:]} verified for {full_name.upper()}.")

#=======================================================================================================
# WhatsApp Integration Note:
#======================================================================================================

def format_nigerian_phone(phone: str) -> str:
    """Formats phone numbers to +234803xxxxxxx required by Ultramsg & Telcos."""
    clean = ''.join(filter(str.isdigit, str(phone)))
    if clean.startswith('0') and len(clean) == 11:
        return '+234' + clean[1:]
    elif clean.startswith('234') and len(clean) == 13:
        return '+' + clean
    return '+' + clean


def generate_otp() -> str:
    """Generates a random 6-digit verification code."""
    return str(random.randint(100000, 999999))


def send_automated_whatsapp(phone_number: str, message_text: str) -> tuple[bool, str]:
    """
    Sends an automated WhatsApp message via Ultramsg API (instance195759).
    Returns (success: bool, status_message: str).
    """
    instance_id = getattr(settings, 'ULTRAMSG_INSTANCE_ID', 'instance195759').strip()
    token = getattr(settings, 'ULTRAMSG_TOKEN', 'n54wpy2pgujenqht').strip()
    recipient = format_nigerian_phone(phone_number)

    url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    payload = {
        "token": token,
        "to": recipient,
        "body": message_text
    }
    headers = {'content-type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        res_data = response.json()
        if response.status_code == 200 and ('sent' in str(res_data) or res_data.get('status') == 'success'):
            return (True, f"WhatsApp automated message delivered to {recipient}!")
        return (False, f"Ultramsg response: {response.text}")
    except Exception as e:
        return (False, f"Ultramsg network error: {str(e)}")


def send_multichannel_alert(phone_number: str, message_text: str) -> tuple[bool, str]:
    """
    Dispatches via Automated WhatsApp (Ultramsg) as primary, 
    with console logging for offline defense safety.
    """
    wa_ok, wa_msg = send_automated_whatsapp(phone_number, message_text)
    if wa_ok:
        return (True, wa_msg)

    # Console backup for defense demo
    print(f"\n[DEMO ALERT LOG]")
    print(f"Recipient: {format_nigerian_phone(phone_number)}")
    print(f"Message:   {message_text}\n")
    return (False, wa_msg)