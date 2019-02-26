from django.db import models

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
    stock = models.FloatField()

    def __str__(self):
        return self.name

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
    status = models.CharField(max_length=200)

# Piece Model

class Piece(models.Model):
    # Hacer otra clase Object que contenga muchas piezas y lleve cuenta de la cantidad impresa, referencia a la orden, etc?
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='pieces')
    scale = models.FloatField()
    copies = models.IntegerField(default=1)
    completed = models.IntegerField(default=0)
    stl = models.FileField(blank=True, null=True)
    gcode = models.ForeignKey(Gcode, on_delete=models.CASCADE, blank=True, null=True)
    filament = models.ForeignKey(Filament, on_delete=models.CASCADE)
    status = models.CharField(max_length=200)
    cost = models.FloatField(null=True, blank=True)
    price = models.FloatField(null=True, blank=True)

# Printer Model

class Printer(models.Model):
    name = models.CharField(max_length=200)
    url = models.CharField(max_length=200, blank=False)
    apikey = models.CharField(max_length=32, blank=False)
    status = models.CharField(max_length=20, default='New')
    remaining_time = models.IntegerField(default=0)
    file_name = models.CharField(max_length=100, blank=True)
    size_x = models.IntegerField(blank=False)
    size_y = models.IntegerField(blank=False)
    size_z = models.IntegerField(blank=False)
    filament = models.ForeignKey(Filament, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name