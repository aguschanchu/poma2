from rest_framework import serializers
from wc_liaison.models import Product, Attribute, Variation, Component, AttributeTerm, Order, OrderItem, Client
from skynet.models import Order as PoMaOrder, Piece, Material, Color, Filament
from datetime import datetime, timedelta

 # Serializers

class AttributeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Attribute class. Property 'uuid' is encoded as 'id'
    """
    id = serializers.IntegerField(source='uuid')

    class Meta:
        model = Attribute
        fields = ('name', 'id')

    def create(self, validated_data):
        attribute = Attribute.objects.update_or_create(uuid=validated_data['uuid'], defaults={'name': validated_data['name']})
        return attribute

class AttributeTermSerializer(serializers.ModelSerializer):
    """
    Serializer for the AttributeTerm class.
    """

    id = serializers.IntegerField(source='uuid')
    name = serializers.CharField(source='option')

    class Meta:
        model = AttributeTerm
        fields = ('id', 'name')

    def create(self, validated_data):
        associated_attribute = Attribute.objects.get(uuid=self.context['attribute_id'])
        attribute_term = AttributeTerm.objects.update_or_create(uuid=validated_data['uuid'], defaults={'option': validated_data['option'], 'attribute':associated_attribute})
        return attribute_term



class VariationAttributeTermSerializer(serializers.ModelSerializer):
    """
    Serializer for the AttributeTerm class to be used to deserialize attribute terms from a variation. Parent attribute is encoded through its 'uuid'
    """
    id = serializers.IntegerField(source='attribute.uuid')

    class Meta:
        model = AttributeTerm
        fields = ('id', 'option')


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
        product, created = Product.objects.update_or_create(product_id=validated_data['product_id'], defaults={'name': validated_data['name'], 'sku': validated_data['sku']})
        product.attributes.clear()
        product_attributes = validated_data.pop('attributes')
        for product_attribute in product_attributes:
            try:
                attribute = Attribute.objects.get(uuid=product_attribute['uuid'])
                product.attributes.add(attribute)
            except Exception as e:
                print(e)
                print(f"Attribute {product_attribute['name']} not found")
        return product

class VariationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Variation class. Property 'variation_id' is encoded as 'id'. Property 'name' is created
    based on parent product name and default attributes before data validation since WooCommerce does not provide it.
    Parent product information is provided through context upon creating serializer instance.
    """
    id = serializers.IntegerField(source='variation_id')
    attributes = VariationAttributeTermSerializer(many=True, source='default_attributes')
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
        variation, created = Variation.objects.update_or_create(variation_id=validated_data['variation_id'], defaults={'sku':validated_data['sku'], 'name': validated_data['name'], 'product':associated_product})
        variation.default_attributes.clear()
        variation_attributes_options = validated_data.pop('default_attributes')
        for variation_option in variation_attributes_options:
            try:
                attribute = Attribute.objects.get(uuid=variation_option['attribute']['uuid'])
                for term in attribute.terms.all():
                    if term.option == variation_option['option']:
                        variation.default_attributes.add(term)
            except Exception as e:
                print(e)
        return variation

class ComponentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Component class.
    """
    variation_id = serializers.IntegerField(source='variation.variation_id')
    class Meta:
        object = Component
        fields = ('quantity', 'stl', 'gcode', 'variation_id')

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for the OrderItem class. Parent order is encoded through its 'uuid'. It is passed on to the
    OrderItemSerializer through context upon instantiation.
    """
    attributes = AttributeTermSerializer(many=True)
    class Meta:
        model = OrderItem
        fields = ('variation_id', 'quantity', 'attributes')

class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for the Order class. Property 'uuid' is encoded through 'order_number'.
    Serializer create() method overwritten to create a main Order from the WooCommerce Order.
    """
    order_number = serializers.IntegerField(source='uuid')
    items = OrderItemSerializer(many=True)
    client = serializers.CharField(source='client.name')
    class Meta:
        model = Order
        fields = ('client', 'order_number', 'items')

    def create(self, validated_data):
        # Get Client
        client,created = Client.objects.get_or_create(name=validated_data['client']['name'])

        # Create WooCommerce Order and regular order
        wc_order = Order(client=client, uuid=validated_data['uuid'])
        wc_order.save()

        order = PoMaOrder(client=client.name, priority=3, due_date=datetime.now()+timedelta(days=5))
        order.save()

        # Create associated WooCommerce Order Items
        for item in validated_data['items']:
            wc_order_item = OrderItem(order=wc_order, variation_id=item['variation_id'], quantity=item['quantity'])
            wc_order_item.save()

            compatible_colors = Color.objects.all()
            compatible_materials = Material.objects.all()

            # Add attribute values to order items
            for item_attribute in item['attributes']:
                # attribute = Attribute.objects.get(uuid=item_attribute['attribute']['uuid'])
                attribute_term = AttributeTerm.objects.get(uuid=item_attribute['uuid'])
                wc_order_item.attributes.add(attribute_term)

                # Filter compatible colors and materials as allowed by each attribute term
                compatible_colors = compatible_colors & attribute_term.color_implications.all()
                compatible_materials = compatible_materials & attribute_term.material_implications.all()

            # Create pieces from variation components
            for component in Variation.objects.get(variation_id=item['variation_id']).components.all():
                piece = Piece(order=order, print_settings=component.print_settings, copies=component.quantity*item['quantity'], stl=component.stl, gcode=component.gcode)
                piece.save()
                print('hasta aca si')

                # Add compatible colors and materials to piece
                for color in compatible_colors:
                    piece.colors.add(color)

                for material in compatible_materials:
                    piece.materials.add(material)

        return wc_order






