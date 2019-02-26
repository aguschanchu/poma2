from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from skynet.models import Color

# on Product Linked/Updated from Woocommerce

class WooCommerceProduct(APIView):

    def post(self, request, format=None):
        try:
            a = 1
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# on Order Confirmation from Woocommerce

class WooCommerceOrder(APIView):

    def post(self, request, format=None):
        try:
            a = 1
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)