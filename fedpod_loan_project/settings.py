from pathlib import Path
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-fedpod-cooperative-loan-secret-key-2026'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['10.210.130.184', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Useful for formatting Naira currency (commas)
    'loans',                    # Our main FEDPOD Loan Application
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fedpod_loan_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Global templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fedpod_loan_project.wsgi.application'


# ==============================================================================
# DATABASE CONFIGURATION (XAMPP MySQL Default + SQLite Defense Fallback)
# ==============================================================================

# PRIMARY: XAMPP MySQL Database Configuration
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'fedpod_loan_db',
#         'USER': 'root',
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#     }
# }

# ==============================================================================
# DATABASE CONFIGURATION (PostgreSQL Default + SQLite Defense Fallback)
# ==============================================================================

# PRIMARY: PostgreSQL Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fedpod_loan_db',
        'USER': 'postgres',
        'PASSWORD': 'sammy123',  
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# FALLBACK FOR DEFENSE: If PostgreSQL service stops, comment out the PostgreSQL
# DATABASES block above and uncomment this SQLite block below:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


# Password validation (Simplified so students can create simple test passwords)
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_redirect'
LOGOUT_REDIRECT_URL = 'landing'

# Map Django messages to Bootstrap 5 alert classes
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# ==============================================================================
# SMSLIVE247 CONFIGURATION (Sub-Account API Key Configured)
# ==============================================================================
SMSLIVE247_API_KEY = '1F857498-BB9E-4D1B-A1E1-1D0DBE2CC630'
SMSLIVE247_SENDER_ID = 'SAMMY1'  # Change to your approved Sender ID on SMSLive247 if different

# ==============================================================================
# ULTRAMSG AUTOMATED WHATSAPP CONFIGURATION (https://ultramsg.com/)
# ==============================================================================
ULTRAMSG_INSTANCE_ID = 'instance195759'
ULTRAMSG_TOKEN = 'n54wpy2pgujenqht'