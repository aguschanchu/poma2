from django.db import models
from skynet.models import Gcode, Color, Material

# WooCommerce API Key Model

class WcApiKey(models.Model):
    url = models.CharField(max_length=200)
    consumer_key = models.CharField(max_length=200)
    consumer_secret = models.CharField(max_length=200)


# Attribute Model

class Attribute(models.Model):
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
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='terms')
    uuid = models.IntegerField(blank=True, null=True)
    option = models.CharField(max_length=200)
    color_implications = models.ManyToManyField(Color, blank=True)
    material_implications = models.ManyToManyField(Material, blank=True)

    def __str__(self):
        return self.option

# Product Model

class Product(models.Model):
    name = models.CharField(max_length=200)
    product_id = models.IntegerField(primary_key=True)
    sku = models.CharField(max_length=200, null=True, blank=True)
    attributes = models.ManyToManyField(Attribute)

    def __str__(self):
        return self.name

# Variation of a product Model

class Variation(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    variation_id = models.CharField(max_length=200)
    sku = models.CharField(max_length=200, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    default_attributes = models.ManyToManyField(AttributeTerm)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.sku

# Component of a variation Model

class Component(models.Model):
    scale = models.FloatField
    quantity = models.IntegerField
    stl = models.FileField(blank=True, null=True)
    gcode = models.ForeignKey(Gcode, on_delete=models.CASCADE, blank=True, null=True)
    variation = models.ForeignKey(Variation, on_delete=models.CASCADE, related_name='components')

# WooCommerce Order Model (necessary?)

class WC_Order(models.Model):
    variation_id = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    attribute_terms = models.ManyToManyField(AttributeTerm)




