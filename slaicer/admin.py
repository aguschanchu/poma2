from django.contrib import admin
from .models import *
from django.utils.html import format_html_join, format_html
from django.contrib.postgres.fields import JSONField
from prettyjson import PrettyJSONWidget

@admin.register(PrinterProfile)
class PrinterProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_quality', 'config_file')
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})}
    }
    readonly_fields = ('bed_size', )

    fieldsets = (
        (None, {
            'fields': ('name', 'base_quality', 'nozzle_diameter', 'config_file', 'config')
        }),
        ('Bed size', {
            'fields': ('bed_size',),
        }),
    )

    def bed_size(self, obj):
        return format_html('<b>x</b>: {x} mm <br><b>y</b>: {y} mm <br> <b>z</b>: {z} mm <br>'.format(x=obj.bed_shape[0], y=obj.bed_shape[1], z=obj.bed_shape[2]))


@admin.register(MaterialProfile)
class MaterialProfileAdmin(admin.ModelAdmin):
    list_display = ('config_name', 'config_file')
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})}
    }


@admin.register(PrintProfile)
class PrintProfileAdmin(admin.ModelAdmin):
    list_display = ('config_name', 'layer_height', 'fill_density', 'config_file')
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})}
    }

    actions = ['refresh_compatible_printers']

    def refresh_compatible_printers(self, request, queryset):
        for q in queryset:
            q.clear_compatible_printers()
            q.add_compatible_printers()
        self.message_user(request, "{} successfully refreshed".format(queryset.count()))

    refresh_compatible_printers.short_description = "Refresh compatible printers"


@admin.register(ConfigurationFile)
class ConfigurationFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'provider', 'file')
    actions = ['import_available_profiles']

    def import_available_profiles(self, request, queryset):
        for q in queryset:
            q.import_available_profiles()
        self.message_user(request, "{} successfully imported".format(queryset.count()))

    import_available_profiles.short_description = "Import available profiles"


@admin.register(AvailableProfile)
class ConfigurationFileAdmin(admin.ModelAdmin):
    list_display = ('profile_type', 'config_name', 'config_file')
    list_filter = ('profile_type',)
    actions = ['import_profile']

    def import_profile(self, request, queryset):
        for q in queryset:
            q.convert()
        self.message_user(request, "{} successfully imported".format(queryset.count()))

    import_profile.short_description = "Import selected profiles"


class GeometryResultInline(admin.StackedInline):
    model = GeometryResult
    fields = ('mean_layer_height', 'image', 'error_log')
    readonly_fields = ('image',)

    def image(self, obj):
        return format_html('<img src=' + obj.plot.url + ' width="40%" height="40%"></img>')


class TweakerResultInline(admin.StackedInline):
    model = TweakerResult
    fields = ('unprintability_factor', 'size_x', 'size_y', 'size_z', 'error_log', 'matrix')
    readonly_fields = ('matrix',)

    def matrix(self, obj):
        return obj.rotation_matrix


@admin.register(GeometryModel)
class GeometryModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'file','orientation_result_ready', 'geometry_result_ready')
    inlines = [GeometryResultInline, TweakerResultInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.create_orientation_result()
        obj.create_geometry_result()

    def orientation_result_ready(self, obj):
        return obj.orientation_result_ready

    def geometry_result_ready(self, obj):
        return obj.geometry_result_ready

    geometry_result_ready.boolean = True
    orientation_result_ready.boolean = True

class SliceConfigurationInline(admin.StackedInline):
    model = SliceConfiguration
    fields = ('printer', 'material', 'print', 'auto_print_profile', 'auto_support')


@admin.register(SliceJob)
class SliceJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'build_time', 'celery_id', 'result_ready')
    inlines = [SliceConfigurationInline,]
    actions = ['launch_tasks']

    def result_ready(self, obj):
        return obj.ready()

    result_ready.boolean = True

    def launch_tasks(self, request, queryset):
        for q in queryset:
            q.launch_task()
        self.message_user(request, "{} successfully launched".format(queryset.count()))

    launch_tasks.short_description = "Launch selected tasks"


@admin.register(SliceConfiguration)
class SliceConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'quoting_profile')

    list_filter = ('quoting_profile',)