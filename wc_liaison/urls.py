from django.conf.urls import url
from wc_liaison import views

urlpatterns = [
    url(r'^get_attributes/$', views.WoocommerceAttributes.as_view()),
    url(r'^serialize_product/$', views.SerializeProduct.as_view()),
    url(r'^get_woocommerce_products/$', views.WooCommerceProduct.as_view())
]