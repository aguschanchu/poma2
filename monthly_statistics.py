import csv
import os
import django
import warnings
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'poma2.settings')
django.setup()
from wc_liaison.models import Order as WC_Order, OrderItem, Product, Variation
from skynet.models import Piece, UnitPiece, Order
from django.db.models import Q



with open('abril.csv', 'w', newline='') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(['Nombre', 'Ventas', 'Facturacion', 'Costo FB', 'Costo Filamento', 'Costo Insumos', 'Tiempo Ideal', 'Ganancias Netas', 'Ganancias/Hora Ideal'])

    total_sales = 0
    total_billing = 0
    total_filament_cost = 0
    total_advertising_cost = 0
    total_input_cost = 0
    total_ideal_print_time = 0

    for product in Product.objects.filter(type='simple'):
        sales = 0
        billing = 0
        filament_cost = 0
        advertising_cost = 0
        input_cost = 0
        ideal_print_time = 0

        for item in OrderItem.objects.filter(item_id=product.product_id):
            sales += item.quantity


            for piece in Piece.objects.filter(Q(order=item.order.associated_order) & Q(woocommerce_component__in=product.components.all())):
                piece_price = 0

                ideal_print_time += piece.quote.build_time*piece.copies
                #TODO order by status
                for unit_piece in piece.unit_pieces.all():
                    if unit_piece.success or unit_piece.pending:
                        piece_price = unit_piece.job.filament.price_per_kg*piece.quote.weight
                        filament_cost += piece_price
                    else:
                        filament_cost += piece_price

        total_sales += sales
        total_billing += billing
        total_filament_cost += filament_cost
        total_advertising_cost += advertising_cost
        total_input_cost += input_cost
        total_ideal_print_time += ideal_print_time

        earnings = billing - filament_cost - advertising_cost - input_cost

        spamwriter.writerow([product.name, str(sales), str(billing), str(advertising_cost), str(filament_cost), str(input_cost), str(ideal_print_time), str(earnings), str(earnings)])

    for variation in Variation.objects.all():
        sales = 0
        billing = 0
        filament_cost = 0
        advertising_cost = 0
        input_cost = 0
        ideal_print_time = 0

        for item in OrderItem.objects.filter(item_id=variation.variation_id):
            sales += item.quantity

            for piece in Piece.objects.filter(
                    Q(order=item.order.associated_order) & Q(woocommerce_component__in=variation.components.all())):
                piece_price = 0

                ideal_print_time += piece.quote.build_time * piece.copies
                # TODO order by status
                for unit_piece in piece.unit_pieces.all():
                    if unit_piece.success or unit_piece.pending:
                        piece_price = unit_piece.job.filament.price_per_kg * piece.quote.weight
                        filament_cost += piece_price
                    else:
                        filament_cost += piece_price

        total_sales += sales
        total_billing += billing
        total_filament_cost += filament_cost
        total_advertising_cost += advertising_cost
        total_input_cost += input_cost
        total_ideal_print_time += ideal_print_time

        earnings = billing - filament_cost - advertising_cost - input_cost

        spamwriter.writerow(
            [variation.name, str(sales), str(billing), str(advertising_cost), str(filament_cost), str(input_cost),
             str(ideal_print_time), str(earnings), str(earnings)])

    spamwriter.writerow(['TOTAL', str(total_sales), '2', '2', '2', '2', '2', '2', '2'])