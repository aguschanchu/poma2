from django.db import models
from skynet.models import Gcode, Color, Material

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
    uuid = models.IntegerField()
    value = models.CharField(max_length=200)
    color_implications = models.ManyToManyField(Color, blank=True)
    material_implications = models.ManyToManyField(Material, blank=True)

# Product Model

class Product(models.Model):
    name = models.CharField(max_length=200)
    product_id = models.IntegerField
    sku = models.CharField(max_length=200)
    attributes = models.ManyToManyField(Attribute)

    def __str__(self):
        return self.name

# Variation of a product Model

class Variation(models.Model):
    name = models.CharField(max_length=200)
    variation_id = models.CharField(max_length=200)
    sku = models.CharField(max_length=200, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    default_attributes = models.ManyToManyField(AttributeTerm)

    def __str__(self):
        return self.name

# Component of a variation Model

class Component(models.Model):
    scale = models.FloatField
    quantity = models.IntegerField
    stl = models.FileField(blank=True, null=True)
    gcode = models.ForeignKey(Gcode, on_delete=models.CASCADE, blank=True, null=True)
    variation = models.ForeignKey(Variation, on_delete=models.CASCADE, related_name='components')

# WooCommerce Order Model

class WC_Order(models.Model):
    variation_id = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    attribute_terms = models.ManyToManyField(AttributeTerm)




