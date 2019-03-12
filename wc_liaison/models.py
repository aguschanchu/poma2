from django.db import models
from skynet.models import Gcode, Color, Material

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
    uuid = models.IntegerField()
    slug = models.CharField(max_length=200)

    def influences_color(self):
        for term in self.terms.all():
            if term.color_implications.all():
                return True
        return False

    def influences_material(self):
        for term in self.terms.all():
            if term.material_implications.all():
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
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='terms')
    uuid = models.IntegerField(blank=True, null=True)
    option = models.CharField(max_length=200)
    color_implications = models.ManyToManyField(Color, blank=True)
    material_implications = models.ManyToManyField(Material, blank=True)

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
    variation_id = models.CharField(max_length=200)
    sku = models.CharField(max_length=200)
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
    scale = models.FloatField
    quantity = models.IntegerField
    stl = models.FileField(blank=True, null=True)
    gcode = models.ForeignKey(Gcode, on_delete=models.CASCADE, blank=True, null=True)
    variation = models.ForeignKey(Variation, on_delete=models.CASCADE, related_name='components')

# WooCommerce Client Model

class Client(models.Model):
    """
    Model for each client in the clients' WooCommerce database. Orders made by the client are accessible through
    self.orders
    """
    name = models.CharField(max_length=200)

# WooCommerce Order Model

class Order(models.Model):
    """
    Model for an order made through WooCommerce. Items in the order are accessible through self.items
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders')
    uuid = models.IntegerField()

class OrderItem(models.Model):
    """
    Model for an item in an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variation_id = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    attributes = models.ManyToManyField(AttributeTerm)




