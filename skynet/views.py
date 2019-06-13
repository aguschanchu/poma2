from django.shortcuts import render
from skynet.models import *
from skynet.serializers import *
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from django.http import Http404
from rest_framework.response import Response


'''
List views
'''

class ListAllPrinters(generics.ListAPIView):
    serializer_class = PrinterSerializer

    def get_queryset(self):
        return Printer.objects.all()


class ListAllPendingFilamentChanges(generics.ListAPIView):
    serializer_class = FilamentChangeSerializer

    def get_queryset(self):
        return FilamentChange.objects.filter(confirmed=False)


class ListAllPendingPrintJobs(generics.ListAPIView):
    serializer_class = PrintJobSerializer

    def get_queryset(self):
        return [p for p in PrintJob.objects.filter(success=None) if p.awaiting_for_bed_removal]


'''
Operations view
'''

class ConfirmFilamentChange(generics.RetrieveUpdateAPIView):
    serializer_class = FilamentChangeSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            obj = FilamentChange.objects.get(id=id)
        except FilamentChange.DoesNotExist:
             raise Http404
        return obj

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.confirmed = True
        obj.save()
        return Response(FilamentChangeSerializer(obj).data)


class ConfirmPrintJobResult(generics.RetrieveUpdateAPIView):
    serializer_class = PrintJobSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            obj = PrintJob.objects.get(id=id)
        except PrintJob.DoesNotExist:
             raise Http404
        return obj

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj.success = serializer.validated_data['success']
        obj.save()
        return Response(serializer.data)

class CancelActiveTaskOnPrinter(generics.RetrieveAPIView):
    serializer_class = PrinterSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            obj = Printer.objects.get(id=id)
            obj.connection.cancel_active_task()
        except Printer.DoesNotExist:
             raise Http404
        return obj

class ResetConnectionOnPrinter(generics.RetrieveAPIView):
    serializer_class = PrinterSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            obj = Printer.objects.get(id=id)
            obj.connection.reset_connection()
        except Printer.DoesNotExist:
             raise Http404
        return obj


class TogglePrinterEnableDisabled(generics.RetrieveAPIView):
    serializer_class = PrinterSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            obj = Printer.objects.get(id=id)
            obj.toggle_enabled_disabled()
        except Printer.DoesNotExist:
             raise Http404
        return obj