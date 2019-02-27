from django.conf.urls import url
from wc_liaison import views

urlpatterns = [
    url(r'^attributes/$', views.WoocommerceAttributes.as_view()),
]