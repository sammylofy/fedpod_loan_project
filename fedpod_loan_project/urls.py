from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Customize Django Admin Header for FEDPOD
admin.site.site_header = "FEDPOD Cooperative Administration"
admin.site.site_title = "FEDPOD Loan Portal"
admin.site.index_title = "System Administration & Audit"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('loans.urls')),
]

# Serve uploaded profile pictures in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)