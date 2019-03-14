from rest_framework import serializers
from django.db import models
from datetime import datetime, timedelta
from skynet.models import Color, Material, Order, Piece, Filament

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

class FilamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filament
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

    def to_internal_value(self, data):
        if 'due_date' not in data:
            data['due_date'] = models.DateField(default=datetime.now()+timedelta(days=5))
        if 'priority' not in data:
            data['priority'] = 3
        return super(OrderSerializer, self).to_internal_value(data)
