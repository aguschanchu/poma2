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

class AttributeTermSerializer(serializers.ModelSerializer):
    """
    Serializer for the AttributeTerm class. Parent attribute is encoded through its 'name' and 'uuid'
    """
    name = serializers.CharField(source='attribute.name')
    id = serializers.IntegerField(source='attribute.uuid')

    class Meta:
        model = AttributeTerm
        fields = ('id', 'name', 'option')

    def to_internal_value(self, data):
        if 'name' not in data:
            try:
                name = Attribute.objects.get(uuid = data['id']).name
                data['name'] = name
            except Exception as e:
                print(e)
                data['name'] = ''
        return super(AttributeTermSerializer, self).to_internal_value(data)

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
        return variation

class ComponentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Component class.
    """
    variation_id = serializers.IntegerField(source='variation.variation_id')
    class Meta:
        object = Component
        fields = ('scale', 'quantity', 'stl', 'variation_id')

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

        order = PoMaOrder(client=client.name, order_number=validated_data['uuid'], priority=3, due_date=datetime.now()+timedelta(days=5))
        order.save()

        # Create associated WooCommerce Order Items
        for item in validated_data['items']:
            wc_order_item = OrderItem(order=wc_order, variation_id=item['variation_id'], quantity=item['quantity'])
            wc_order_item.save()

            compatible_colors = Color.objects.all()
            compatible_materials = Material.objects.all()

            # Add attribute values to order items
            for item_attribute in item['attributes']:
                attribute = Attribute.objects.get(uuid=item_attribute['attribute']['uuid'])
                attribute_term = AttributeTerm.objects.get(attribute=attribute, option=item_attribute['option'])
                wc_order_item.attributes.add(attribute_term)

                # Filter compatible colors and materials as allowed by each attribute term
                compatible_colors = compatible_colors & attribute_term.color_implications.all()
                compatible_materials = compatible_materials & attribute_term.material_implications.all()

            # Get all filaments compatible with the appropiate color and material restrictions
            compatible_filaments = Filament.objects.filter(color__in=compatible_colors, material__in=compatible_materials)

            # Create pieces from variation components
            for component in Variation.objects.get(variation_id=item['variation_id']).components.all():
                piece = Piece(order=order, scale=component.scale, copies=component.quantity*item['quantity'], stl=component.stl, status='Accepted')
                piece.save()

                # Add compatible filaments to piece
                for compatible_filament in compatible_filaments:
                    piece.filaments.add(compatible_filament)

        return wc_order






