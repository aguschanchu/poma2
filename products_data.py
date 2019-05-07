import csv
import os
import django
import warnings
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'poma2.settings')
django.setup()

from wc_liaison.models import Product, Variation

with open('products_data.csv', 'w', newline='') as products_data:
    writer = csv.writer(products_data, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['name', 'id', 'type', 'file_type', 'price', 'stl_name', 'stl_scale',
                     'stl_layer_height', 'gcode_name', 'gcode_printer', 'gcode_material', 'quantity'])

    for product in Product.objects.all():
        if product.type=='simple':
            writer.writerow([product.name, str(product.product_id), product.type])
        elif product.type=='variable':
            for variation in product.variations.all():
                writer.writerow([variation.name, str(variation.variation_id), product.type])