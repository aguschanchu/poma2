from rest_framework import serializers
from wc_liaison.models import Product, Attribute

 # Serializers

class AttributeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='uuid')
    class Meta:
        model = Attribute
        fields = ('name', 'id')

class ProductSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True)
    id = serializers.IntegerField(source='product_id')
    class Meta:
        model = Product
        fields = ('name', 'id', 'sku', 'attributes')

    def create(self, validated_data):
        product_attributes = validated_data.pop('attributes')
        product = Product(name=validated_data['name'], product_id=validated_data['product_id'], sku=validated_data['sku'])
        product.save()
        for product_attribute in product_attributes:
            print(product_attribute)
            try:
                attribute = Attribute.objects.get(uuid=product_attribute['uuid'])
                product.attributes.add(attribute)
            except:
                print("Attribute not found")
        return product
