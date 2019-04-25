from rest_framework import serializers
from django.db import models
from skynet.models import *
from slaicer.models import PrintProfile

class PrinterTypeSimplifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrinterProfile
        fields = ('id', 'name', 'printer_model', 'bed_shape', 'base_quality', 'nozzle_diameter')


class FilamentSimplifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filament
        fields = ('id', 'bed_temperature', 'nozzle_temperature', 'brand', 'color', 'material')
        depth = 1


class OctoprintConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OctoprintConnection
        depth = 2
        fields = ('id', 'url', 'locked', 'active_task', 'status')


class PrinterSerializer(serializers.ModelSerializer):
    printer_type = PrinterTypeSimplifiedSerializer()
    filament = FilamentSimplifiedSerializer()
    connection = OctoprintConnectionSerializer()

    class Meta:
        model = Printer
        fields = '__all__'
        depth = 3

class PrinterSimplifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = '__all__'


class FilamentChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilamentChange
        fields = ('id', 'created', 'new_filament', 'printer')
        depth = 2

    printer = PrinterSimplifiedSerializer(source='get_printer')


class PrintJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintJob
        fields = '__all__'

    printer = PrinterSimplifiedSerializer(source='get_printer')
