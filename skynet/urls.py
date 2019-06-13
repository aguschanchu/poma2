from django.conf.urls import url, include
from skynet import views
from django.urls import path


urlpatterns = []


# List views
urlpatterns += [
    path('list/printers/', views.ListAllPrinters.as_view(), name='printers'),
    path('list/pending_filament_changes/', views.ListAllPendingFilamentChanges.as_view(), name='pending_filament_change'),
    path('list/print_jobs_pending_for_confirmation/', views.ListAllPendingPrintJobs.as_view(), name='print_jobs_pending_for_confirmation')
]

# Operations views
urlpatterns += [
    path('operations/confirm_filament_change/<int:id>/', views.ConfirmFilamentChange.as_view()),
    path('operations/confirm_job_result/<int:id>/', views.ConfirmPrintJobResult.as_view()),
    path('operations/cancel_active_task/<int:id>/', views.CancelActiveTaskOnPrinter.as_view()),
    path('operations/reset_printer/<int:id>/', views.ResetConnectionOnPrinter.as_view()),
    path('operations/toggle_printer_en_dis/<int:id>/', views.TogglePrinterEnableDisabled.as_view()),
]
