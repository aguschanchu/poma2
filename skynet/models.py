from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

# Color Model


class Color(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Material Model

class Material(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=200)
    print_bed_temp = models.IntegerField()
    print_nozzle_temp = models.IntegerField()

    def __str__(self):
        return self.name


# Filament Provider Model

class FilamentProvider(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=200)
    telephone = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name


# Material Brand Model

class MaterialBrand(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    providers = models.ManyToManyField(FilamentProvider, blank=True)

    def __str__(self):
        return self.name


# Filament Model

class Filament(models.Model):
    name = models.CharField(max_length=200, blank=True)
    sku = models.CharField(max_length=200)
    brand = models.ForeignKey(MaterialBrand, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    print_bed_temp = models.IntegerField(blank=True)
    print_nozzle_temp = models.IntegerField(blank=True)
    price_per_kg = models.IntegerField(null=True, blank=True)
    density = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.name


# Filament Purchase Model

class FilamentPurchase(models.Model):
    filament = models.ForeignKey(Filament, on_delete=models.CASCADE)
    provider = models.ForeignKey(FilamentProvider, on_delete=models.CASCADE)
    quantity = models.FloatField()  # En kg
    date = models.DateField()


# Ready to print GCODE Model

class Gcode(models.Model):
    print_file = models.FileField()
    filament = models.ForeignKey(Filament, on_delete=models.CASCADE)


# Order Models

class Order(models.Model):
    client = models.CharField(max_length=200)
    order_number = models.IntegerField()
    due_date = models.DateField()
    priority = models.IntegerField()


# Piece Quality Model

class PrintSettings(models.Model):
    name = models.CharField(max_length=200)
    config_file = models.FileField()

    def __str__(self):
        return self.name


# Piece Model

class Piece(models.Model):

    # TODO Define all possible states for a piece

    # Hacer otra clase Object que contenga muchas piezas y lleve cuenta de la cantidad impresa, referencia a la orden, etc?
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='pieces')
    scale = models.FloatField(default=1.0)
    print_settings = models.ForeignKey(PrintSettings, on_delete=models.CASCADE, blank=True, null=True)
    copies = models.IntegerField(default=1)
    completed = models.IntegerField(default=0)
    stl = models.FileField(blank=True, null=True)
    gcode = models.ForeignKey(
        Gcode, on_delete=models.CASCADE, blank=True, null=True)
    filaments = models.ManyToManyField(Filament)
    status = models.CharField(max_length=200)
    weight = models.FloatField(null=True, blank=True)
    time = models.DurationField(null=True, blank=True)


class Scenario(models.Model):
    uuid = models.IntegerField(default=0)


class PrintOrder(models.Model):
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="print_orders")


# Printer Type Model

class PrinterType(models.Model):
    name = models.CharField(max_length=200)
    uuid = models.IntegerField()
    size_x = models.IntegerField()
    size_y = models.IntegerField()
    size_z = models.IntegerField()

    def __str__(self):
        return self.name


# Printer Model

class Printer(models.Model):
    name = models.CharField(max_length=200)
    uuid = models.IntegerField()
    printer_type = models.ForeignKey(PrinterType, on_delete=models.CASCADE)
    url = models.CharField(max_length=200, blank=False)
    apikey = models.CharField(max_length=32, blank=False)
    status = models.CharField(max_length=20, default='New')
    remaining_time = models.DurationField(default=0)
    file_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


# PrintJob Model
class PrintJob(models.Model):
    printer = models.ForeignKey(Printer, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    estimated_time = models.DurationField(null=True, blank=True)


class PrintJobPiece(models.Model):
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    print_job = models.ForeignKey(PrintJob, related_name="print_job_pieces", on_delete=models.CASCADE)


class TentativePrintJob(models.Model):
    print_job = models.ForeignKey(
        PrintJob, on_delete=models.CASCADE, related_name="print_job")
    print_order = models.ForeignKey(
        PrintOrder, on_delete=models.CASCADE, related_name="print_orders")
    position = models.IntegerField()


class UnitPiece(models.Model):
    piece = models.ForeignKey(Piece, related_name='unit_pieces', on_delete=models.CASCADE)
    position = models.IntegerField(null=True, blank=True)
    print_order = models.ForeignKey(PrintOrder, on_delete=models.CASCADE)
    tentative_pj = models.ForeignKey(TentativePrintJob, null=True, blank=True, on_delete=models.CASCADE)
