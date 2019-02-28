from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from skynet.models import Color
from wc_liaison.models import WC_APIKey, Attribute, AttributeTerm, Product
from urllib.parse import urlencode
from woocommerce import API
from wc_liaison.serializers import ProductSerializer

# on API Key requested to Woocommerce

class WooCommerceRequestAPIKey(APIView):

    def post(self, request, format=None):
        try:
            url = request.data['url']

        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# Synchronize Woocommerce attributes

class WoocommerceAttributes(APIView):

    def get(self, request, format=None):
        try:
            # Get API Key and create a WooCommerce API instance
            api_key = WC_APIKey.objects.all()[0]
            wcapi = API(url=api_key.url, consumer_key=api_key.consumer_key, consumer_secret=api_key.consumer_secret, wc_api=True, version="wc/v2")

            # Get list of attributes in WooCommerce
            attributes = wcapi.get("products/attributes").json()
            for attribute in attributes:
                # If attribute does not exist, add it
                try:
                    Attribute.objects.get(uuid=attribute['id'])
                except:
                    new_attribute = Attribute(name=attribute['name'], uuid=attribute['id'], slug=attribute['slug'])
                    new_attribute.save()
                # Get list of attribute terms
                attribute_terms = wcapi.get(f"products/attributes/{attribute['id']}/terms").json()
                for term in attribute_terms:
                    # If term does not exist, add it
                    try:
                        AttributeTerm.objects.get(uuid=term['id'])
                    except:
                        new_term = AttributeTerm(attribute=new_attribute, uuid=term['id'], value=term['name'])
                        new_term.save()
            return Response(status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# on Product Linked/Updated from Woocommerce

class WooCommerceProduct(APIView):

    def get(self, request, format=None):
        try:
            # Get API Key and create a WooCommerce API instance
            api_key = WC_APIKey.objects.all()[0]
            wcapi = API(url=api_key.url, consumer_key=api_key.consumer_key, consumer_secret=api_key.consumer_secret,
                        wc_api=True, version="wc/v2")

            products_in_store = wcapi.get("products?per_page=100&type=variable").json()
            products = ProductSerializer(data=products_in_store, many=True)
            if products.is_valid():
                products.save()
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_201_CREATED)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# on Order Confirmation from Woocommerce

class WooCommerceOrder(APIView):

    def post(self, request, format=None):
        try:
            a = 1
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class SerializeProduct(APIView):

    def get(self, request, format=None):
        try:
            product = Product.objects.get(name='Luna 140mm')
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        try:
            serializer = ProductSerializer(data=request.data, many=True)
            if serializer.is_valid():
                print(serializer.validated_data)
                serializer.save()
            return Response(status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
