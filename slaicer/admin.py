from django.contrib import admin
from .models import *


@admin.register(PrinterProfile)
class PrinterProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_quality', 'config_file')


@admin.register(MaterialProfile)
class MaterialProfileAdmin(admin.ModelAdmin):
    list_display = ('config_name', 'material', 'config_file', 'valid_profile')

    def valid_profile(self, obj):
        return False if obj.material is None else True

    valid_profile.boolean = True

@admin.register(PrintProfile)
class PrintProfileAdmin(admin.ModelAdmin):
    list_display = ('config_name', 'layer_height', 'fill_density', 'config_file')


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


