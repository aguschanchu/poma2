from django.db import models
from skynet.models import Gcode, Color, Material, Order as SkynetOrder
from slaicer.models import GeometryModel, PrintProfile
from django.utils import timezone

# WooCommerce API Key Model

class WcApiKey(models.Model):
    url = models.CharField(max_length=200)
    consumer_key = models.CharField(max_length=200)
    consumer_secret = models.CharField(max_length=200)


# Attribute Model

class Attribute(models.Model):
    """
    Model for each attribute present in the clients' WooCommerce. Methods influences_color and influences_material
    indicate wether any of the possible values of this attribute have implications on the color and material, respectively, with which
    to print.
    """
    name = models.CharField(max_length=200)
    uuid = models.IntegerField(primary_key=True)

    @property
    def influences_color(self):
        for term in self.terms.all():
            if Color.objects.all().difference(term.color_implications.all()):
                return True
        return False

    @property
    def influences_material(self):
        for term in self.terms.all():
            if Material.objects.all().difference(term.material_implications.all()):
                return True
        return False

    def __str__(self):
        return self.name

#  Attribute Term Model

class AttributeTerm(models.Model):
    """
    Model for each attribute value possibility as defined in the clients' WooCommerce. Properties color_implications
    and material_implications indicate color and materials, respectively, compatible with the corresponding attribute value, if any.
    """

    def available_colors(self):
        return Color.objects.all()

    def available_materials(self):
        return Material.objects.all()

    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='terms')
    uuid = models.IntegerField(primary_key=True)
    option = models.CharField(max_length=200)
    color_implications = models.ManyToManyField(Color, blank=True, default=available_colors('self'))
    material_implications = models.ManyToManyField(Material, blank=True, default=available_materials('self'))

    def __str__(self):
        return self.option

# Product Model

class Product(models.Model):
    """
    Model for each product in the clients' WooCommerce. Variations associated to this product, if any, are available through
    self.variations
    """
    name = models.CharField(max_length=200)
    product_id = models.IntegerField(primary_key=True)
    sku = models.CharField(max_length=200, null=True, blank=True)
    type = models.CharField(max_length=200)
    attributes = models.ManyToManyField(Attribute)

    def __str__(self):
        return self.name

# Variation of a product Model

class Variation(models.Model):
    """
    Model for each variation of a variable product in the clients' WooCommerce. Components to print are accessible through
    self.components
    """
    name = models.CharField(max_length=200, blank=True, null=True)
    variation_id = models.IntegerField(primary_key=True)
    sku = models.CharField(max_length=200, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    default_attributes = models.ManyToManyField(AttributeTerm)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.sku

# Component of a variation Model

class Component(models.Model):
    """
    Model for a component of a variation or a simple product in the clients' WooCommerce. Components hold the information
    for a specific file to print, such as the STL/OBJ file itself, its scale and the amount needed.
    """
    print_settings = models.ForeignKey(PrintProfile, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    stl = models.ForeignKey(GeometryModel, on_delete=models.SET_NULL, null=True, blank=True)
    gcode = models.ForeignKey(Gcode, on_delete=models.SET_NULL, blank=True, null=True)
    variation = models.ForeignKey(Variation, on_delete=models.SET_NULL, related_name='variation_components', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name='product_components', null=True, blank=True, limit_choices_to={'type': 'simple'})

# WooCommerce Client Model

class Customer(models.Model):
    """
    Model for each client in the clients' WooCommerce database. Orders made by the client are accessible through
    self.orders
    """

    uuid = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    username = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# WooCommerce Order Model

class Order(models.Model):
    """
    Model for an order made through WooCommerce. Items in the order are accessible through self.items
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    created = models.DateTimeField(default=timezone.now)
    associated_order = models.ForeignKey(SkynetOrder, on_delete=models.CASCADE, related_name='woocommerce_order', null=True)
    uuid = models.IntegerField(primary_key=True)

class OrderItem(models.Model):
    """
    Model for an item in an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_id = models.CharField(max_length=200)
    item_type = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    attributes = models.ManyToManyField(AttributeTerm)




