from django.urls import path
from . import views

urlpatterns = [
    # Visitor & Auth
    path('', views.landing_page, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    # Customer Routes
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/profile/', views.complete_profile, name='complete_profile'),
    path('customer/verify-phone/', views.send_or_verify_phone_otp, name='verify_phone'),
    path('customer/verify-bvn/', views.verify_bvn_action, name='verify_bvn'),
    path('customer/apply/', views.apply_loan, name='apply_loan'),
    path('customer/repayment/<int:repayment_id>/pay/', views.customer_pay_installment, name='customer_pay_installment'),
    path('loan/<int:loan_id>/result/', views.loan_result, name='loan_result'),
    path('loan/<int:loan_id>/detail/', views.loan_detail, name='loan_detail'),

    # Loan Manager Routes
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/loan/<int:loan_id>/decision/', views.process_loan_decision, name='process_loan_decision'),
    path('manager/repayment/<int:repayment_id>/record/', views.record_repayment, name='record_repayment'),
    path('manager/repayment/<int:repayment_id>/remind-sms/', views.send_due_sms_reminder, name='send_due_sms_reminder'),
    path('manager/reports/', views.reports_view, name='reports'),
]