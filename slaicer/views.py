from django.shortcuts import render
from rest_framework import generics, status, pagination, serializers
from .models import GeometryResult
from .serializers import GeometryResultSerializer
from django.shortcuts import get_object_or_404

'''
Internal views
'''

# Used to post plots made by workers on the database server
class UpdateGeometryResult(generics.UpdateAPIView):
    lookup_url_kwarg = 'id'
    serializer_class = GeometryResultSerializer

    def get_queryset(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        gr = get_object_or_404(GeometryResult, pk=id)
        return gr

