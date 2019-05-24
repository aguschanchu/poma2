import os


def superuser_setup(User):
    #Superuser config
    username = 'admin'
    email = 'creame3d@creame3d.com'
    password = 'Outreach'

    u = User.objects.create_superuser(username, email, password)


def site_config(Site):
    #Site onfig
    Site.objects.all()[0].delete()
    site = Site.objects.get_or_create(domain=settings.CURRENT_HOST, name=settings.CURRENT_HOST, id=1)[0]
    print("Configuring site settings. Please check that this information is correct:")
    print("Current host: {host} \nCurrent protocol: {protocol} \nCurrent port: {port}".format(**{'host': settings.CURRENT_HOST,
                                                                                               'protocol': settings.CURRENT_PROTOCOL,
                                                                                               'port': settings.CURRENT_PORT}))

def check_for_lib():
    global os, warnings
    if not os.path.isdir('slaicer/lib'):
        warnings.warn("Libraries aren't configured correctly. Please run slaicer/populare_lib.sh")


def set_octoprint_dispatcher_scheduler():
    global PeriodicTask, IntervalSchedule
    schedule, created = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.SECONDS)
    PeriodicTask.objects.create(interval=schedule,
                                name='Octoprint dispatcher',
                                task='skynet.tasks.octoprint_task_dispatcher')

def set_scheduler_keepalive():
    global PeriodicTask, IntervalSchedule
    schedule, created = IntervalSchedule.objects.get_or_create(every=10, period=IntervalSchedule.SECONDS)
    PeriodicTask.objects.create(interval=schedule,
                                name='Scheduler keepalive',
                                task='skynet.scheduler.scheduler_service')
'''
The following functions are used as an example, and for development purposes. Please DON'T use it in production enviorments
'''

def hypercube_profiles_setup():
    global slaicer_models, requests, ContentFile
    # Content file creation
    cf = slaicer_models.ConfigurationFile.objects.create(name='Perfile hypercube', version='0.1', vendor='C3D', provider='https://www.dropbox.com/s/znjvyiojypjabku/slicer_vzh10yg.ini?dl=1')
    r = requests.get('https://www.dropbox.com/s/znjvyiojypjabku/slicer_vzh10yg.ini?dl=1')
    cf.file.save('hypercube.ini', ContentFile(r.content))
    cf.import_available_profiles()
    # Available profiles import
    for o in slaicer_models.AvailableProfile.objects.all():
        o.convert()

def prusa_profiles_setup():
    global slaicer_models, requests, ContentFile
    # Content file creation
    cf = slaicer_models.ConfigurationFile.objects.create(name='Prusa-settings', version='0.4.5', vendor='Prusa', provider='https://raw.githubusercontent.com/prusa3d/Slic3r-settings/master/live/PrusaResearch/0.4.5.ini')
    r = requests.get('https://raw.githubusercontent.com/prusa3d/Slic3r-settings/master/live/PrusaResearch/0.4.5.ini')
    cf.file.save('prusa.ini', ContentFile(r.content))
    cf.import_available_profiles()
    # Available profiles import
    for o in slaicer_models.AvailableProfile.objects.all():
        if o.config_name in ['Original Prusa i3 MK3', 'Prusa PLA', '0.15mm QUALITY MK3', '0.20mm QUALITY MK3', '0.10mm DETAIL MK3', '0.05mm ULTRADETAIL MK3']:
            o.convert()
    # Quoting profile creation
    slaicer_models.SliceConfiguration.objects.create(printer=slaicer_models.PrinterProfile.objects.last(), material=slaicer_models.MaterialProfile.objects.last(), quoting_profile=True)

def filament_setup():
    global slaicer_models, requests, ContentFile, skynet_models
    fp = skynet_models.FilamentProvider.objects.create(name="3D Insumos")
    mb = skynet_models.MaterialBrand.objects.create(name="MKP")
    mb.providers.add(fp)
    mat = skynet_models.Material.objects.create(name="PLA", density=1.24, profile=slaicer_models.MaterialProfile.objects.first())
    colors = {'blanco': 'FFFFFF', 'negro': '000000'}
    for color in colors.keys():
        c = skynet_models.Color.objects.create(name=color, code=colors[color])
        skynet_models.Filament.objects.create(brand=mb, color=c, material=mat, price_per_kg=400)


def c3d_printers_setup():
    from skynet import models as skynet_models
    global slaicer_models, requests, ContentFile
    # Hypercubes
    oc = skynet_models.OctoprintConnection.objects.create(url='http://octoprint1.creame3d.com:8002/', apikey='699725A09ECA40A0A9D4BBFF6647AF1A')
    pp = slaicer_models.PrinterProfile.filter(name="C3D+").first()
    skynet_models.Printer.objects.create(name="C3D+", printer_type=pp, connection=oc, filament=skynet_models.Filament.objects.first())
    oc = skynet_models.OctoprintConnection.objects.create(url='http://octoprint1.creame3d.com:8007/', apikey='8C31C1772FEF40C58C2374432619FF18')
    pp = slaicer_models.PrinterProfile.filter(name="C3D+K").first()
    skynet_models.Printer.objects.create(name="C3D+K", printer_type=pp, connection=oc, filament=skynet_models.Filament.objects.first())

def prusa_printers_setup():
    from skynet import models as skynet_models
    global slaicer_models, requests, ContentFile
    oc = skynet_models.OctoprintConnection.objects.create(url='http://octoprint1.creame3d.com:8011/', apikey='699725A09ECA40A0A9D4BBFF6647AF1A')
    pp = slaicer_models.PrinterProfile.filter(name="Original Prusa i3 MK3").first()
    skynet_models.Printer.objects.create(name="Prusa MK3-OB", printer_type=pp, connection=oc, filament=skynet_models.Filament.objects.first())





if __name__ == '__main__':
    print('\n' + ('=' * 80) + '\n')
    import django
    import warnings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'poma2.settings')
    django.setup()
    from django.contrib.auth.models import User
    from django.conf import settings
    from django.contrib.sites.models import Site
    from slaicer import models as slaicer_models
    from skynet import models as skynet_models
    import requests
    from django.core.files.base import ContentFile
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    import os
    import subprocess

    print('Populating Database...')
    print('----------------------\n')
    superuser_setup(User)
    site_config(Site)
    check_for_lib()
    set_octoprint_dispatcher_scheduler()
    hypercube_profiles_setup()
    prusa_profiles_setup()
    filament_setup()


