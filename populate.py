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
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    import os
    import subprocess
    print('Populating Database...')
    print('----------------------\n')
    superuser_setup(User)
    site_config(Site)
    check_for_lib()
    set_octoprint_dispatcher_scheduler()

