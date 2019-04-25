from django.shortcuts import render
from skynet.models import *
from skynet.serializers import *
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView


'''
List views
'''

class ListAllPrinters(generics.ListAPIView):
    serializer_class = PrinterSerializer

    def get_queryset(self):
        return Printer.objects.all()


class ListAllPendingFilamentChanges(generics.ListAPIView):
    serializer_class =  FilamentChangeSerializer

    def get_queryset(self):
        return FilamentChange.objects.filter(confirmed=False)


class ListAllPendingPrintJobs(generics.ListAPIView):
    serializer_class = PrintJobSerializer

    def get_queryset(self):
        return [p for p in PrintJob.objects.filter(success=None) if p.awaiting_for_bed_removal]




