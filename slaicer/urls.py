from django.conf.urls import url, include
from django.urls import path
from slaicer import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'slaicer'

urlpatterns = []

#Internal views
urlpatterns += [
    path('update/geometry_result/<int:id>/', views.UpdateGeometryResult.as_view(), name='update_geometry_result')]
