from rest_framework import serializers

from .models import GeometryResult

class GeometryResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeometryResult
        fields = '__all__'

