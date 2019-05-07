import csv
import os
import django
import warnings
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'poma2.settings')
django.setup()

from skynet.models import Gcode, Material
from wc_liaison.models import Product, Variation, Component
from slaicer.models import  GeometryModel, PrinterProfile
from django.conf import settings


with open('products_data.csv', newline='') as component_data:
    reader = csv.reader(component_data, delimiter=',')
    for row in reader:
        if row[2]=='variable':
            try:
                variation = Variation.objects.get(variation_id=row[1])
                if row[3] == 'gcode':
                    material = Material.objects.get(name=row[10])
                    printer_profile = PrinterProfile.objects.get(name=row[9])
                    gcode = Gcode.objects.create(print_file=row[8], printer_type=printer_profile, material=material)
                    Component.objects.create(variation=variation, gcode=gcode, quantity=row[11])
                elif row[3] == 'stl':
                    stl=GeometryModel.objects.create(file=row[5], scale=row[6], quality=row[7])
                    Component.objects.create(variation=variation, stl=stl, quantity=row[11])
            except Exception as e:
                print(f"Component for variation #{row[1]} couldn't be created. Error: {e}")

        elif row[2]=='simple':
            try:
                product = Product.objects.get(product_id=row[1])
                if row[3] == 'gcode':
                    material = Material.objects.get(name=row[10])
                    printer_profile = PrinterProfile.objects.get(name=row[9])
                    gcode = Gcode.objects.create(print_file=row[8], printer_type=printer_profile, material=material)
                    Component.objects.create(product=product, gcode=gcode, quantity=row[11])
                elif row[3] == 'stl':
                    stl = GeometryModel.objects.create(file=row[5], scale=row[6], quality=row[7])
                    Component.objects.create(product=product, stl=stl, quantity=row[11])
            except Exception as e:
                print(f"Component for product #{row[1]} couldn't be created. Error: {e}")






