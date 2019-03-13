from django.contrib import admin
from wc_liaison.models import Attribute, AttributeTerm, Product, Variation, Component, WcApiKey, OrderItem, Order, Client

# Register your models here.

class WC_APIKeyAdmin(admin.ModelAdmin):
    list_display = ('url', 'consumer_key', 'consumer_secret')

class AttributeAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'slug','influences_color', 'influences_material')
    fields = ('name', 'slug', 'uuid')

    def influences_color(self, obj):
        for term in obj.terms.all():
            if term.color_implications.all():
                return True
        return False

    def influences_material(self, obj):
        for term in obj.terms.all():
            if term.material_implications.all():
                return True
        return False

class AttributeTermAdmin(admin.ModelAdmin):
    list_display = ('option', 'parent_attribute', 'color_references', 'material_references')

    def parent_attribute(self, obj):
        return obj.attribute.name

    def color_references(self, obj):
        return " - ".join([color.name for color in obj.color_implications.all()])

    def material_references(self, obj):
        return " - ".join([material.name for material in obj.material_implications.all()])

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_id', 'product_attributes')

    def product_attributes(self, obj):
        return " - ".join([p.name for p in obj.attributes.all()])

class VariationAdmin(admin.ModelAdmin):
    list_display = ('name', 'variation_id', 'parent_product')

    def parent_product(self, obj):
        return obj.product.name

class ComponentAdmin(admin.ModelAdmin):
    list_display = ('stl', 'scale', 'quantity', 'parent_variation')

    def parent_variation(self, obj):
        return obj.variation.name

class ClientAdmin(admin.ModelAdmin):
    list_display = ('name',)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'client_name', 'items')

    def client_name(self, obj):
        return obj.client.name

    def items(self, obj):
        return " - ".join([f"{item.quantity}x {Variation.objects.get(variation_id=item.variation_id).name} " + ", ".join([attribute.option for attribute in item.attributes.all()]) for item in obj.items.all()])


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'variation_id', 'variation_name', 'quantity', 'attribute_values')

    def order_number(self, obj):
        return obj.order.uuid

    def variation_name(self, obj):
        try:
            variation = Variation.objects.get(variation_id=obj.variation_id)
            return variation.name
        except Exception as e:
            print(e)
            return "Name not available"

    def attribute_values(self, obj):
        return " - ".join([f"{attribute_term.attribute.name}: {attribute_term.option}" for attribute_term in obj.attributes.all()])


admin.site.register(WcApiKey, WC_APIKeyAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(AttributeTerm, AttributeTermAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(Component, ComponentAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Client, ClientAdmin)