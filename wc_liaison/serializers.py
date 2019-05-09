from rest_framework import serializers
from wc_liaison.models import Product, Attribute, Variation, Component, AttributeTerm, Order, OrderItem, Customer
from skynet.models import Order as PoMaOrder, Piece, Material, Color, Filament
from datetime import datetime, timedelta
from django.utils import timezone
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

    def to_internal_value(self, data):
        if 'name' not in data:
            try:
                attribute_term=AttributeTerm.objects.get(uuid=data['id'])
                data['name']=attribute_term.name
            except:
                data['name'] = f'Attribute term #{data["id"]}'
        return super(AttributeTermSerializer, self).to_internal_value(data)

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
        fields = ('name', 'id', 'sku', 'type', 'attributes')

    def create(self, validated_data):
        product, created = Product.objects.update_or_create(product_id=validated_data['product_id'], defaults={'name': validated_data['name'], 'sku': validated_data['sku'], 'type': validated_data['type']})
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

class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Customer class.
    """
    id = serializers.IntegerField(source='uuid')

    class Meta:
        model = Customer
        fields = ('id', 'first_name', 'last_name', 'email', 'username')

    def create(self, validated_data):
        customer = Customer.objects.update_or_create(uuid=validated_data['id'], defaults={'first_name':validated_data['first_name'], 'last_name':validated_data['last_name'], 'email':validated_data['email'], 'username':validated_data['username']})
        return customer

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for the OrderItem class. Parent order is encoded through its 'uuid'. It is passed on to the
    OrderItemSerializer through context upon instantiation.
    """
    attributes = AttributeTermSerializer(many=True)
    class Meta:
        model = OrderItem
        fields = ('item_id', 'item_type', 'quantity', 'attributes')

class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for the Order class. Property 'uuid' is encoded through 'order_number'.
    Serializer create() method overwritten to create a main Order from the WooCommerce Order.
    """
    order_number = serializers.IntegerField(source='uuid')
    items = OrderItemSerializer(many=True)
    customer = CustomerSerializer()
    class Meta:
        model = Order
        fields = ('customer', 'order_number', 'items')

    def create(self, validated_data):
        # Get Client
        customer, created = Customer.objects.update_or_create(uuid=validated_data['customer']['uuid'], defaults={'first_name':validated_data['customer']['first_name'], 'last_name':validated_data['customer']['last_name'], 'email':validated_data['customer']['email'], 'username':validated_data['customer']['username']})


        # Create WooCommerce Order and regular order
        order = PoMaOrder(client=f"{customer.first_name} {customer.last_name}", priority=3,
                          due_date=datetime.now() + timedelta(days=5))
        order.save()

        wc_order = Order(customer=customer, associated_order=order, created=timezone.now(), uuid=validated_data['uuid'])
        wc_order.save()

        # Create associated WooCommerce Order Items
        for item in validated_data['items']:
            wc_order_item = OrderItem(order=wc_order, item_id=item['item_id'], item_type=item['item_type'], quantity=item['quantity'])
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

            if item['item_type']=="variable":
                components = Variation.objects.get(variation_id=item['item_id']).variation_components.all()
            elif item['item_type']=="simple":
                components = Product.objects.get(product_id=item['item_id']).product_components.all()

            # Create pieces from variation components
            for component in components:
                piece = Piece(order=order, print_settings=component.print_settings, copies=component.quantity*item['quantity'], stl=component.stl, gcode=component.gcode, woocommerce_components=component)
                piece.save()

                # Add compatible colors and materials to piece
                for color in compatible_colors:
                    piece.colors.add(color)

                for material in compatible_materials:
                    piece.materials.add(material)

        return wc_order






