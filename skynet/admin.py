from django.contrib import admin
from skynet.models import Color, Material, FilamentProvider, MaterialBrand, Filament

# Register your models here.

class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    fields = ('name',)

class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'print_bed_temp', 'print_nozzle_temp')
    fields = ('name', 'print_bed_temp', 'print_nozzle_temp')

class FilamentProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'telephone')
    fields = ('name', 'telephone')

class MaterialBrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'filament_providers')
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('providers',),
        }),
    )

    def filament_providers(self, obj):
        return "\n".join([p.name for p in obj.providers.all()])

class FilamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'color', 'material', 'print_bed_temp', 'print_nozzle_temp', 'density', 'price_per_kg', 'stock')
    fieldsets = (
        (None, {
            'fields': ('brand', 'color', 'material', 'stock')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('name', 'print_bed_temp', 'print_nozzle_temp', 'density', 'price_per_kg'),
        }),
    )

class PieceAdmin(admin.ModelAdmin):
    list_display = ()

class OrderAdmin(admin.ModelAdmin):
    list_display = ()

class PrinerAdmin(admin.ModelAdmin):
    list_display = ()

admin.site.register(Color, ColorAdmin)
admin.site.register(Material, MaterialAdmin)
admin.site.register(FilamentProvider, FilamentProviderAdmin)
admin.site.register(MaterialBrand, MaterialBrandAdmin)
admin.site.register(Filament, FilamentAdmin)
