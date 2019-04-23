from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from skynet.models import Color
from wc_liaison.models import WcApiKey, Attribute, AttributeTerm, Product
from urllib.parse import urlencode
from woocommerce import API
from wc_liaison.serializers import ProductSerializer, VariationSerializer, OrderSerializer, OrderItemSerializer
from django.conf import settings

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
            # Create a WooCommerce API instance
            wcapi = API(url=settings.WOOCOMMERCE_URL, consumer_key=settings.CONSUMER_KEY,
                        consumer_secret=settings.CONSUMER_SECRET,
                        wc_api=True, version="wc/v2")

            # Get list of attributes in WooCommerce
            attributes = wcapi.get("products/attributes?per_page=100").json()
            for attribute in attributes:
                # If attribute does not exist, add it
                try:
                    current_attribute = Attribute.objects.get(uuid=attribute['id'])
                except:
                    current_attribute = Attribute(name=attribute['name'], uuid=attribute['id'], slug=attribute['slug'])
                    current_attribute.save()
                # Get list of attribute terms
                attribute_terms = wcapi.get(f"products/attributes/{attribute['id']}/terms?per_page=100").json()
                for term in attribute_terms:
                    # If term does not exist, add it
                    try:
                        AttributeTerm.objects.get(uuid=term['id'])
                    except:
                        new_term = AttributeTerm(attribute=current_attribute, uuid=term['id'], option=term['name'])
                        new_term.save()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)

# on Product Linked/Updated from Woocommerce

class WooCommerceProduct(APIView):

    def get(self, request, format=None):
        try:
            # Create a WooCommerce API instance
            wcapi = API(url=settings.WOOCOMMERCE_URL, consumer_key=settings.CONSUMER_KEY, consumer_secret=settings.CONSUMER_SECRET,
                        wc_api=True, version="wc/v2")

            products_in_store = wcapi.get("products?per_page=100&type=variable").json()
            products = ProductSerializer(data=products_in_store, many=True)
            if products.is_valid():
                products.save()
                for product in products.validated_data:
                    variations_in_store = wcapi.get(f"products/{product['product_id']}/variations").json()
                    variations = VariationSerializer(data=variations_in_store, many=True, context={'product_name': product['name'], 'product_id':product['product_id']})
                    if variations.is_valid():
                        variations.save()
                    else:
                        print(variations.errors)
            else:
                print(products.errors)
                return Response(status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)


# on Order Confirmation from Woocommerce

class WooCommerceOrder(APIView):

    def post(self, request, format=None):
        try:
            serializer=OrderSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_201_CREATED)
            else:
                print("WooCommerce Order Serializer not valid. Reason: ")
                print(serializer.errors)
                return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)