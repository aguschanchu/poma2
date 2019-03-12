from rest_framework import serializers
from wc_liaison.models import Product, Attribute, Variation, AttributeTerm

 # Serializers

class AttributeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Attribute class. Property 'uuid' is encoded as 'id'
    """
    id = serializers.IntegerField(source='uuid')
    class Meta:
        model = Attribute
        fields = ('name', 'id')

class AttributeTermSerializer(serializers.ModelSerializer):
    """
    Serializer for the AttributeTerm class. Parent attribute is encoded through its 'name' and 'uuid'
    """
    name = serializers.CharField(source='attribute.name')
    id = serializers.IntegerField(source='attribute.uuid')
    class Meta:
        model = AttributeTerm
        fields = ('id', 'name', 'option')

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer fot the Product class. Property 'product_id' is encoded as 'id'. Create method is overwritten
    """
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
            try:
                attribute = Attribute.objects.get(uuid=product_attribute['uuid'])
                product.attributes.add(attribute)
            except:
                print(f"Attribute {product_attribute['name']} not found")
        return product

class VariationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Variation class. Property 'variation_id' is encoded as 'id'. Property 'name' is created
    based on parent product name and default attributes before data validation since WooCommerce does not provide it.
    Parent product information is provided through context upon creating serializer instance.
    """
    id = serializers.IntegerField(source='variation_id')
    attributes = AttributeTermSerializer(many=True, source='default_attributes')
    class Meta:
        model = Variation
        fields = ('name', 'sku', 'id', 'attributes')

    # Add 'name' property based on parent product name and variation default attributes
    # before data validation if necessary
    def to_internal_value(self, data):
        if 'name' not in data:
            data['name'] = self.context['product_name']
            for attribute in data['attributes']:
                data['name'] = data['name'] + f" - {attribute['option']}"
        return super(VariationSerializer, self).to_internal_value(data)

    # Overwritten method create() to assign default attributes
    def create(self, validated_data):
        associated_product = Product.objects.get(product_id=self.context['product_id'])
        variation = Variation(sku=validated_data['sku'], variation_id=validated_data['variation_id'], name=validated_data['name'], product=associated_product)
        variation.save()
        variation_attributes_options = validated_data.pop('default_attributes')
        for variation_option in variation_attributes_options:
            try:
                attribute = Attribute.objects.get(uuid=variation_option['attribute']['uuid'])
                for term in attribute.terms.all():
                    if term.option == variation_option['option']:
                        variation.default_attributes.add(term)
            except Exception as e:
                print(e)

