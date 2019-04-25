from django.conf.urls import url, include
from skynet import views
from django.urls import path


urlpatterns = []


# List views
urlpatterns += [
    path('printers/', views.ListAllPrinters.as_view(), name='printers'),
    path('pending_filament_changes', views.ListAllPendingFilamentChanges.as_view(), name='pending_filament_change'),
    path('print_jobs_pending_for_confirmation', views.ListAllPendingPrintJobs.as_view(), name='print_jobs_pending_for_confirmation')
]
