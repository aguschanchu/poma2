from rest_framework import serializers
from django.db import models
from skynet.models import *
from slaicer.models import PrintProfile
import datetime

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
    printing = serializers.BooleanField()
    human_int_req = serializers.BooleanField()
    idle = serializers.BooleanField()
    printer_connection_enabled = serializers.BooleanField()

    def time_left_get(self, obj):
        if obj.connection.active_task is None:
            return ''
        else:
            return str(datetime.timedelta(seconds=round(obj.connection.active_task.time_left)))

    time_left = serializers.SerializerMethodField('time_left_get')


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

    printer = PrinterSimplifiedSerializer(source='get_printer', required=False)
