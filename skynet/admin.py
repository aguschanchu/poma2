from django.contrib import admin
from skynet.models import *
from django.utils.html import format_html_join, format_html

# Register your models here.

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', )

@admin.register(FilamentProvider)
class FilamentProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'telephone')
    fields = ('name', 'telephone')

@admin.register(MaterialBrand)
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

@admin.register(Filament)
class FilamentAdmin(admin.ModelAdmin):
    list_display = ('brand', 'color', 'material', 'bed_temperature', 'nozzle_temperature', 'price_per_kg', 'stock')
    fieldsets = (
        (None, {
            'fields': ('brand', 'color', 'material')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('bed_temperature', 'nozzle_temperature'),
        }),
    )

    def stock(self, obj):
        current_stock = 0
        for purchase in FilamentPurchase.objects.all():
            current_stock += purchase.quantity
        return current_stock

    def name(self, obj):
        return obj.name


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ('order', 'copies',  'stl', 'build_time', 'weight')

    def build_time(self, obj):
        return obj.get_build_time()

    def weight(self, obj):
        return obj.get_weight()

class PieceInline(admin.TabularInline):
    model = Piece
    extra = 0
    readonly_fields = ('completed_pieces', 'ready')

    def completed_pieces(self, obj):
        return obj.completed_pieces

    def ready(self, obj):
        return True if obj.completed_pieces == obj.copies else False

    ready.boolean = True

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('client', 'due_date', 'priority', 'ready')
    inlines = (PieceInline,)

    def ready(self, obj):
        return True if all([x.completed_pieces == x.copies for x in obj.pieces.all()]) else False

    ready.boolean = True

class OctoprintStatusInline(admin.StackedInline):
    model = OctoprintStatus

@admin.register(OctoprintConnection)
class OctoprintConnectionAdmin(admin.ModelAdmin):
    list_display = ('url', 'apikey', 'active_task_running')
    readonly_fields = ('temperature', 'estimated_time_left')
    fieldsets = (
        (None, {
            'fields': ('url', 'apikey', 'active_task', 'temperature', 'estimated_time_left'),
        }),
    )
    inlines = [OctoprintStatusInline]

    def active_task_running(self, obj):
        return False if obj.active_task is None else True

    def temperature(self, obj):
        return "Tool: {tool}, Bed: {bed}".format(tool=obj.status.temperature.tool, bed=obj.status.temperature.bed)

    def estimated_time_left(self, obj):
        return obj.status.job.estimated_print_time_left


    active_task_running.boolean = True

@admin.register(OctoprintTask)
class OctoprintTaskAdmin(admin.ModelAdmin):
    list_display = ('connection', 'type', 'file', 'job_sent', 'ready', 'awaiting_for_human_intervention')
    actions = ['cancel_tasks']

    def cancel_tasks(self, request, queryset):
        queryset.update(cancelled=True)
        for o in queryset:
            if hasattr(o, 'print_job'):
                self.active_task.print_job.success = False
                self.active_task.print_job.save()
        self.message_user(request, "{} successfully cancelled".format(queryset.count()))

    cancel_tasks.short_description = "Cancel tasks"

    def ready(self, obj):
        return obj.ready

    def awaiting_for_human_intervention(self, obj):
        return obj.awaiting_for_human_intervention

    ready.boolean = True
    awaiting_for_human_intervention.boolean = True

@admin.register(Gcode)
class GcodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'print_file', 'printer_type')


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ('name', 'printer_ready')



@admin.register(FilamentChange)
class FilamentChangeAdmin(admin.ModelAdmin):
    list_display = ('id', 'new_filament', 'confirmed', 'printer')
    actions = ['confirm_change']

    def printer(self, obj):
        return obj.task.connection.printer

    def confirm_change(self, request, queryset):
        queryset.update(confirmed=True)
        self.message_user(request, "{} successfully confirmed".format(queryset.count()))

    confirm_change.short_description = "Confirm filament change"


class UnitPieceInline(admin.TabularInline):
    model = UnitPiece
    classes = ['collapse']


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'filament', 'printing', 'awaiting_for_bed_removal', 'success')
    inlines = [UnitPieceInline]

    def printing(self, obj):
        return obj.printing

    def awaiting_for_bed_removal(self, obj):
        return obj.awaiting_for_bed_removal

    printing.boolean = True
    awaiting_for_bed_removal.boolean = True


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'launched_tasks_count', 'processing_time', 'status')
    readonly_fields = ('print_schedule_disp',)

    def launched_tasks_count(self, obj):
        return obj.launched_tasks.count()

    def processing_time(self, obj):
        return (obj.finished - obj.created).total_seconds() if obj.finished is not None else None

    def print_schedule_disp(self, obj):
        s = ''
        for line in obj.print_schedule():
            if 'Machine' in line:
                s += '<b>{}</b>'.format(line)
            else:
                s += line
            s += '<br>'
        return format_html(s)



