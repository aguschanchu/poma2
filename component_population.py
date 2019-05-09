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
from django.core.files import File


with open('products_data.csv', newline='') as component_data:
    reader = csv.reader(component_data, delimiter=',')
    for row in reader:
        if row[2]=='variable':
            try:
                variation = Variation.objects.get(variation_id=row[1])
                if row[3] == 'gcode':

                    filenames = []
                    for filename in row[8].split('|'):
                        filenames.append(filename)

                    materials = []
                    for indicated_material in row[10].split('|'):
                        materials.append(Material.objects.get(name=indicated_material))

                    printer_profiles = []
                    for profile in row[9].split('|'):
                        printer_profiles.append(PrinterProfile.objects.get(name=profile))

                    quantities = []
                    for quantity in row[11].split('|'):
                        quantities.append(quantity)

                    for i, filename in enumerate(row[8].split('|')):
                        gcode = Gcode(printer_type=printer_profiles[min(i, printer_profiles.index(printer_profiles[-1]))], material=materials[min(i, materials.index(materials[-1]))])
                        gcode.print_file.save(filename, File(open(settings.BASE_DIR + '/component_files/gcodes/' + filename, 'r')))
                        Component.objects.create(variation=variation, gcode=gcode, quantity=quantities[min(i, quantities.index(quantities[-1]))])

                    # material = Material.objects.get(name=row[10])
                    # printer_profile = PrinterProfile.objects.get(name=row[9])
                    # gcode = Gcode(printer_type=printer_profile, material=material)
                    # gcode.print_file.save(row[8], File(open(settings.BASE_DIR + '/component_files/gcodes/' + row[8], 'r')))
                    #
                    # Component.objects.create(variation=variation, gcode=gcode, quantity=row[11])

                elif row[3] == 'stl':

                    scales = []
                    for scale in row[6].split('|'):
                        scales.append(scale)

                    qualities = []
                    for quality in row[7].split('|'):
                        qualities.append(quality)

                    quantities = []
                    for quantity in row[11].split('|'):
                        quantities.append(quantity)

                    for i, filename in enumerate(row[5].split('|')):
                        stl = GeometryModel.objects.create(scale=scales[min(i, scales.index(scales[-1]))], quality=qualities.index(qualities[-1]))
                        try:
                            stl.file.save(filename, File(open(settings.BASE_DIR + '/component_files/stl/' + filename, 'r')))
                            print(f"STL #{variation.variation_id} was Text")
                        except:
                            stl.file.save(filename,
                                          File(open(settings.BASE_DIR + '/component_files/stl/' + filename, 'rb')))
                            print(f"STL #{variation.variation_id} was Binary")

                        Component.objects.create(variation=variation, stl=stl, quantity=quantities[min(i, quantities.index(quantities[-1]))])

                    # stl=GeometryModel.objects.create(scale=row[6], quality=row[7])
                    # try:
                    #     stl.file.save(row[5], File(open(settings.BASE_DIR +'/component_files/stl/' + row[5], 'r')))
                    #     print(f"STL #{variation.variation_id} was Text")
                    # except:
                    #     stl.file.save(row[5], File(open(settings.BASE_DIR +'/component_files/stl/' + row[5], 'rb')))
                    #     print(f"STL #{variation.variation_id} was Binary")
                    #
                    # Component.objects.create(variation=variation, stl=stl, quantity=row[11])

            except Exception as e:
                print(f"Component for variation #{row[1]} couldn't be created. Error: {e}")

        elif row[2]=='simple':
            try:
                product = Product.objects.get(product_id=row[1])
                if row[3] == 'gcode':

                    filenames = []
                    for filename in row[8].split('|'):
                        filenames.append(filename)

                    materials = []
                    for indicated_material in row[10].split('|'):
                        materials.append(Material.objects.get(name=indicated_material))

                    printer_profiles = []
                    for profile in row[9].split('|'):
                        printer_profiles.append(PrinterProfile.objects.get(name=profile))

                    quantities = []
                    for quantity in row[11].split('|'):
                        quantities.append(quantity)

                    for i, filename in enumerate(row[8].split('|')):
                        gcode = Gcode(
                            printer_type=printer_profiles[min(i, printer_profiles.index(printer_profiles[-1]))],
                            material=materials[min(i, materials.index(materials[-1]))])
                        gcode.print_file.save(filename, File(
                            open(settings.BASE_DIR + '/component_files/gcodes/' + filename, 'r')))
                        Component.objects.create(product=product, gcode=gcode,
                                                 quantity=quantities[min(i, quantities.index(quantities[-1]))])

                    # material = Material.objects.get(name=row[10])
                    # printer_profile = PrinterProfile.objects.get(name=row[9])
                    # gcode = Gcode.objects.create(printer_type=printer_profile, material=material)
                    # gcode.print_file.save(row[8], File(open(settings.BASE_DIR + '/component_files/gcodes/' + row[8], 'r')))
                    #
                    # Component.objects.create(product=product, gcode=gcode, quantity=row[11])

                elif row[3] == 'stl':

                    scales = []
                    for scale in row[6].split('|'):
                        scales.append(scale)

                    qualities = []
                    for quality in row[7].split('|'):
                        qualities.append(quality)

                    quantities = []
                    for quantity in row[11].split('|'):
                        quantities.append(quantity)

                    for i, filename in enumerate(row[5].split('|')):
                        stl = GeometryModel.objects.create(scale=scales[min(i, scales.index(scales[-1]))],
                                                           quality=qualities.index(qualities[-1]))
                        try:
                            stl.file.save(filename,
                                          File(open(settings.BASE_DIR + '/component_files/stl/' + filename, 'r')))
                            print(f"STL #{variation.variation_id} was Text")
                        except:
                            stl.file.save(filename,
                                          File(open(settings.BASE_DIR + '/component_files/stl/' + filename, 'rb')))
                            print(f"STL #{variation.variation_id} was Binary")

                        Component.objects.create(product=product, stl=stl,
                                                 quantity=quantities[min(i, quantities.index(quantities[-1]))])

                    # stl = GeometryModel.objects.create(scale=row[6], quality=row[7])
                    #
                    # try:
                    #     stl.file.save(row[5], File(open(settings.BASE_DIR +'/component_files/stl/' + row[5], 'r')))
                    #     print(f"STL #{product.product_id} was Text")
                    # except:
                    #     stl.file.save(row[5], File(open(settings.BASE_DIR +'/component_files/stl/' + row[5], 'rb')))
                    #     print(f"STL #{product.product_id} was Binary")
                    #
                    # Component.objects.create(product=product, stl=stl, quantity=row[11])

            except Exception as e:
                print(f"Component for product #{row[1]} couldn't be created. Error: {e}")






