import csv
import os
import django
import warnings
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'poma2.settings')
django.setup()
from wc_liaison.models import Order, OrderItem, Product, Variation

with open('abril.csv', 'w', newline='') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(['Nombre', 'Ventas', 'Facturacion', 'Costo FB', 'Costo Filamento', 'Costo Insumos', 'Tiempo Ideal', 'Ganancias Netas', 'Ganancias/Hora Ideal'])
    for product in Product.objects.filter(type='simple'):
        sales = 0
        for item in OrderItem.objects.filter(item_id=product.product_id):
            sales += item.quantity

        spamwriter.writerow([product.name, '2', '2', '2', '2', '2', '2', '2', '2'])
    for variation in Variation.objects.all():
        sales = 0
        for item in OrderItem.objects.filter(item_id=variation.variation_id):
            sales += item.quantity

        spamwriter.writerow([variation.name, str(sales), '2', '2', '2', '2', '2', '2', '2'])

    spamwriter.writerow(['TOTAL', '2', '2', '2', '2', '2', '2', '2', '2'])