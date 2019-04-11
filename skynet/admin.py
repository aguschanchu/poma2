from django.contrib import admin
from skynet.models import *

# Register your models here.

class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)

class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', )

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
    list_display = ('name', 'brand', 'color', 'material', 'bed_temperature', 'nozzle_temperature', 'price_per_kg', 'stock')
    fieldsets = (
        (None, {
            'fields': ('brand', 'color', 'material')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('name', 'bed_temperature', 'nozzle_temperature', 'density', 'price_per_kg'),
        }),
    )

    def stock(self, obj):
        current_stock = 0
        for purchase in FilamentPurchase.objects.all():
            current_stock += purchase.quantity
        return current_stock


class PieceAdmin(admin.ModelAdmin):
    list_display = ('order', 'scale', 'copies',  'stl', 'build_time', 'weight')

    def build_time(self, obj):
        return obj.get_build_time()

    def weight(self, obj):
        return obj.get_weight()


class OrderAdmin(admin.ModelAdmin):
    list_display = ('client', 'due_date', 'priority')

class PrinterAdmin(admin.ModelAdmin):
    list_display = ()

admin.site.register(Color, ColorAdmin)
admin.site.register(Material, MaterialAdmin)
admin.site.register(FilamentProvider, FilamentProviderAdmin)
admin.site.register(MaterialBrand, MaterialBrandAdmin)
admin.site.register(Filament, FilamentAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Piece, PieceAdmin)

@admin.register(OctoprintConnection)
class OctoprintConnectionAdmin(admin.ModelAdmin):
    list_display = ('url', 'apikey', 'active_task_running')
    fieldsets = (
        (None, {
            'fields': ('url', 'apikey', 'active_task')
        }),
    )

    def active_task_running(self, obj):
        return False if obj.active_task is None else True

    active_task_running.boolean = True

@admin.register(OctoprintTask)
class OctoprintTaskAdmin(admin.ModelAdmin):
    list_display = ('connection', 'type', 'file', 'job_sent', 'ready')

    def ready(self, obj):
        return obj.ready

    ready.boolean = True

@admin.register(Gcode)
class GcodeAdmin(admin.ModelAdmin):
    list_display = ('id',)
