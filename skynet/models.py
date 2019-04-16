from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator, MinLengthValidator
import urllib3
from urllib3.util import Retry
from urllib3 import PoolManager, ProxyManager, Timeout
from urllib3.exceptions import MaxRetryError
from urllib.parse import urljoin
urllib3.disable_warnings()
from celery.result import AsyncResult
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import json
from django.core.exceptions import ValidationError
from django.core.files import File
import random, string
import traceback
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import timedelta
from slaicer.models import *
from skynet.tasks import quote_gcode
from django.core.files.base import ContentFile

'''
Materials and colors model definition
'''

# Color Model
class Color(models.Model):
    name = models.CharField(max_length=100)
    #Hex color code
    code = models.CharField(max_length=6, validators=[MinLengthValidator(6)])

    def __str__(self):
        return self.name


# Material Model

class Material(models.Model):
    name = models.CharField(max_length=200)
    density = models.FloatField(blank=True, null=True)
    profile = models.ForeignKey('slaicer.MaterialProfile', on_delete=models.CASCADE)

    def __str__(self):
        return self.name



# Filament Provider Model

class FilamentProvider(models.Model):
    name = models.CharField(max_length=200)
    telephone = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name


# Material Brand Model

class MaterialBrand(models.Model):
    name = models.CharField(max_length=200)
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
    bed_temperature = models.IntegerField(blank=True, null=True)
    nozzle_temperature = models.IntegerField(blank=True, null=True)
    price_per_kg = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

    def get_bed_temperature(self):
        return self.bed_temperature if self.bed_temperature is not None else self.material.profile.bed_temperature

    def get_nozzle_temperature(self):
        return self.nozzle_temperature if self.bed_temperature is not None else self.material.profile.nozzle_temperature


# Filament Purchase Model

class FilamentPurchase(models.Model):
    filament = models.ForeignKey(Filament, on_delete=models.CASCADE)
    provider = models.ForeignKey(FilamentProvider, on_delete=models.CASCADE)
    quantity = models.FloatField()  # En kg
    date = models.DateField(default=timezone.now)



'''
OctoprintConnection handles API endpoints with octoprint
'''

class FilamentChangeManager(models.Manager):
    def issue_change(self, new_filament, connection):
        o = self.create(new_filament=new_filament)
        old_filament = connection.printer.filament
        gcode = "M104 S{nozzle_temp} \nM140 S{bed_temp} \n G28".format(bed_temp=max(new_filament.get_bed_temperature(), old_filament.get_bed_temperature()),
                                                                        nozzle_temp=max(new_filament.get_nozzle_temperature(), old_filament.get_nozzle_temperature()))
        o.task = connection.create_task(file=ContentFile(gcode))
        o.save()
        return o


class FilamentChange(models.Model):
    new_filament = models.ForeignKey(Filament, on_delete=models.CASCADE)
    task = models.OneToOneField('OctoprintTask', on_delete=models.CASCADE, related_name='filament_change', null=True)
    confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    confirmed_date = models.DateTimeField(null=True)

    objects = FilamentChangeManager()

    @staticmethod
    def filament_change_mean_duration():
        # Time that takes a filament change. The idea es to calculate this automatically, based on previous events
        return 15*60


@receiver(pre_save, sender=FilamentChange)
def update_printer_filament_on_confirmation(sender, instance, update_fields, **kwargs):
    if instance.confirmed:
        printer = instance.task.connection.printer
        printer.filament = instance.new_filament
        printer.save()


class OctoprintTaskManager(models.Manager):
    def create_task(self, connection, commands=None, file=None, slicejob=None):
        # It's a valid task?
        if len([x for x in [connection, commands, file] if x is not None]) == 1:
            raise ValidationError("Please specify a command or a file or a slicejob")
        if file is not None:
            file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + '.gcode'
            o = self.create(type='job', connection=connection)
            o.file.save(file_name, file)
        if commands is not None:
            # So, it's a command task. Before, we check if the object received is a file, or just a string
            if hasattr(commands, 'open'):
                commands = commands.open('r').read()
            o = self.create(type='command', commands=commands, connection=connection)
        else:
            o = self.create(type='slice-and-print-job', slicejob=slicejob, connection=connection)
        return o


class OctoprintTask(models.Model):
    task_types = (('command', 'Command'),
                  ('job', 'Print job'),
                  ('slice-and-print-job', 'Slice and print job'))
    celery_id = models.CharField(max_length=200, null=True)
    connection = models.ForeignKey('OctoprintConnection', on_delete=models.CASCADE, related_name='tasks')
    type = models.CharField(choices=task_types, default='job', max_length=200)
    # Accepts multiple commands, separated each one with a newline ('\n')
    commands = models.TextField(null=True)
    file = models.FileField(null=True)
    slicejob = models.ForeignKey('slaicer.SliceJob', null=True, on_delete=models.SET_NULL, blank=True)
    # Used to track task status
    job_sent = models.BooleanField(default=False)
    job_filename = models.CharField(max_length=300, null=True)
    objects = OctoprintTaskManager()
    # We support task dependency (something similar to celery chains)
    dependency = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='dependencies')

    @property
    def status(self):
        if self.celery_id is None:
            return 'PENDING'
        else:
            return AsyncResult(self.celery_id).state

    @property
    def slice_job_ready(self):
        if self.slicejob is None:
            return True
        else:
            return self.slicejob.ready()

    @property
    def ready(self):
        if not self.slice_job_ready:
            return False
        if self.celery_id is None:
            return False
        else:
            return AsyncResult(self.celery_id).ready()

    @property
    def awaiting_for_human_intervention(self):
        if hasattr(self, 'filament_change'):
            return not self.filament_change.confirmed
        if hasattr(self, 'print_job'):
            return self.print_job.awaiting_for_bed_removal
        return False

    @property
    def finished(self):
        return self.ready and not self.awaiting_for_human_intervention

    @property
    def time_left(self):
        # TODO: Handle time planning better when we have slicejobs in progress
        if not self.slice_job_ready:
            self.slicejob.get_estimated_build_time()
        if hasattr(self, 'filament_change'):
            return FilamentChange.filament_change_mean_duration()
        if hasattr(self, 'print_job'):
            if self.print_job.awaiting_for_bed_removal:
                return 60*15
            else:
                return self.connection.status.job.estimated_print_time_left
        return 1

    @property
    def dependencies_ready(self):
        return (self.dependency.dependencies_ready and self.dependency.finished) if self.dependency is not None else True

    def get_file(self):
        if self.type == 'job':
            return self.file
        else:
            return self.slicejob.gcode


class OctoprintJobStatus(models.Model):
    name = models.CharField(max_length=300, null=True)
    estimated_print_time = models.IntegerField(null=True)
    estimated_print_time_left = models.IntegerField(null=True)


class OctoprintTemperature(models.Model):
    tool = models.FloatField(null=True)
    bed = models.FloatField(null=True)


class OctoprintStatus(models.Model):
    cancelling = models.BooleanField(default=False)
    closedOrError = models.BooleanField(default=False)
    error = models.BooleanField(default=False)
    finishing = models.BooleanField(default=False)
    operational = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)
    pausing = models.BooleanField(default=False)
    printing = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    resuming = models.BooleanField(default=False)
    sdReady = models.BooleanField(default=False)
    connectionError = models.BooleanField(default=False)
    last_update = models.DateTimeField(auto_now=True)
    temperature = models.OneToOneField(OctoprintTemperature, on_delete=models.CASCADE, null=True)
    job = models.OneToOneField(OctoprintJobStatus, on_delete=models.CASCADE, null=True)
    connection = models.OneToOneField('OctoprintConnection', null=True, on_delete=models.CASCADE, related_name='status')

    @property
    def instance_ready(self):
        return self.ready and not self.connectionError

    @property
    def printer_disabled(self):
        return self.closedOrError or self.connectionError

class OctoprintConnection(models.Model):
    url = models.CharField(max_length=300, validators=[URLValidator(schemes=['http', 'https'])])
    apikey = models.CharField(max_length=200)
    active_task = models.ForeignKey(OctoprintTask, on_delete=models.SET_NULL, null=True, blank=True)
    # If the connection is locked, no new tasks will be executed from the queue.
    locked = models.BooleanField(default=False)
    # Octoprint flags


    @staticmethod
    def _get_connection_pool():
        retry_policy = Retry(total=3, status_forcelist=list(range(405, 501)))
        timeout_policy = Timeout(read=10, connect=5)
        return PoolManager(retries=retry_policy, timeout=timeout_policy)

    def _get_connection_headers(self, json_content: bool = True):
        if json_content:
            return {'x-api-key': self.apikey, 'Content-Type': 'application/json'}
        else:
            return {'x-api-key': self.apikey}

    def _issue_command(self, commands: str):
        fields = {'commands': commands.split('\n')}
        r = self._get_connection_pool().request('POST', urljoin(self.url, 'api/printer/command'),
                                                headers=self._get_connection_headers(),
                                                body=json.dumps(fields).encode('utf-8'))
        if r.status == 204:
            return True
        else:
            raise MaxRetryError("Error sending command to instance")

    def _print_file(self, file: File):
        # Accepts Django File or ContentFile class
        file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + '.gcode' if file.name is None else file.name
        with file.open('r') as f:
            # We add a M400 command at the end of the file, so, we avoid problems due marlin gcode cache
            file_content = f.read() + '\nM400 \nM115'
            r = json.loads(self._get_connection_pool().request('POST', urljoin(self.url, 'api/files/local'),
                                                               headers=self._get_connection_headers(json_content=False),
                                                               fields={'print': True,
                                                                       'file': (file_name, file_content)}).data.decode('utf-8'))

        if r.get('done'):
            return file_name
        else:
            raise MaxRetryError("Error sending command to instance")

    @property
    def connection_ready(self):
        return not self.locked and self.status.instance_ready

    @property
    def awaiting_for_human_intervention(self):
        return self.active_task.awaiting_for_human_intervention if self.active_task is not None else False

    @property
    def active_task_ready_or_free(self):
        return self.active_task.ready if self.active_task is not None else True

    @property
    def printer_ready(self):
        return self.connection_ready and self.active_task_ready_or_free and not self.awaiting_for_human_intervention

    @property
    def time_left(self):
        return self.active_task.time_left if self.active_task is not None else 0

    # Check if octoprint API url is valid
    def ping(self):
        try:
            r = self._get_connection_pool().request('GET', urljoin(self.url, 'api/version'),
                                                    headers=self._get_connection_headers())
        except MaxRetryError:
            return False
        if r.status == 200:
            return True
        else:
            return False

    def update_status(self):
        try:
            # Instance status
            r = json.loads(self._get_connection_pool().request('GET', urljoin(self.url, 'api/printer'),
                                                               headers=self._get_connection_headers()).data.decode('utf-8'))
            OctoprintStatus.objects.filter(connection=self).update(**r['state']['flags'], connectionError = False)
            self.refresh_from_db()
            if 'temperature' in r.keys():
                self.status.temperature.tool = r['temperature'].get('tool0')['actual'] if r['temperature'].get('tool0') is not None else None
                self.status.temperature.bed = r['temperature'].get('bed')['actual'] if r['temperature'].get('bed') is not None else None
                self.status.temperature.save()
            # Job status
            r = json.loads(self._get_connection_pool().request('GET', urljoin(self.url, 'api/job'),
                                                               headers=self._get_connection_headers()).data.decode('utf-8'))
            self.status.job.name = r['job']['file']['name']
            self.status.job.estimated_print_time = r['job']['estimatedPrintTime']
            self.status.job.estimated_print_time_left = r['progress']['printTimeLeft']
            self.status.job.save()
        except:
            traceback.print_exc()
            self.status.connectionError = True
            self.status.save()

    def create_task(self, commands=None, file=None, slicejob=None):
        return OctoprintTask.objects.create_task(self, commands=commands, file=file, slicejob=slicejob)


@receiver(pre_save, sender=OctoprintConnection)
def validate_octoprint_connection_on_creation(sender, instance, update_fields, **kwargs):
    # No update_fields were specified, so, probably it's a new instance
    if not update_fields:
        if not instance.ping():
            raise ValidationError("Error on connecting to octoprint instance")

@receiver(post_save, sender=OctoprintConnection)
def create_octoprint_state(sender, instance, created, **kwargs):
    if created:
        o = OctoprintStatus.objects.create(job=OctoprintJobStatus.objects.create(),
                                           temperature=OctoprintTemperature.objects.create(),
                                           connection=instance)
        # Status update scheduling
        # TODO: Modify update period accordingly to task
        schedule, created = IntervalSchedule.objects.get_or_create(every=2, period=IntervalSchedule.SECONDS)
        PeriodicTask.objects.create(interval=schedule,
                                    name='Update OctoprintConnection id {}'.format(instance.id),
                                    task='skynet.tasks.update_octoprint_status',
                                    kwargs=json.dumps({'conn_id': instance.id}))


'''
Printers models definitions
'''

# Printer Model
class Printer(models.Model):
    name = models.CharField(max_length=200)
    printer_type = models.ForeignKey('slaicer.PrinterProfile', on_delete=models.CASCADE)
    connection = models.OneToOneField(OctoprintConnection, related_name='printer', on_delete=models.CASCADE)
    filament = models.ForeignKey(Filament, null=True, on_delete=models.SET_NULL)
    # Used to disable manually the printer from the system
    disabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def printer_ready(self):
        return self.connection.printer_ready

    @property
    def printer_enabled(self):
        return not (self.disabled or self.connection.status.printer_disabled)

'''
Orders models definitions
'''


# Ready to print GCODE Model

class Gcode(models.Model):
    print_file = models.FileField(upload_to='gcode/')
    printer_type = models.ForeignKey('slaicer.PrinterProfile', on_delete=models.SET_NULL, null=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True)
    build_time = models.FloatField(default=None, blank=True, null=True)
    weight = models.FloatField(default=None, blank=True, null=True)
    celery_id = models.CharField(max_length=200, null=True, blank=True)

    def ready(self):
        return False if self.celery_id is None else AsyncResult(self.celery_id).ready()


# Order Models
def order_default_due_date():
    return timezone.now() + timedelta(days=4)

class Order(models.Model):
    client = models.CharField(max_length=200)
    due_date = models.DateField(default=order_default_due_date)
    priority = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=3)


# Piece Model

class Piece(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='pieces')
    # If it's none, they will be calculated automatically
    print_settings = models.ForeignKey('slaicer.PrintProfile', on_delete=models.SET_NULL, blank=True, null=True)
    copies = models.IntegerField(default=1)
    scale = models.FloatField(default=1.0)
    material = models.ManyToManyField(Material)
    color = models.ManyToManyField(Color)
    # Used to mark the piece as canceled
    cancelled = models.BooleanField(default=False)
    # You need to specify a model or a Gcode (but not both). The field is called stl for historical reasons, but it supports obj too
    stl = models.ForeignKey(GeometryModel, on_delete=models.CASCADE, null=True, blank=True)
    gcode = models.ForeignKey(Gcode, on_delete=models.CASCADE, blank=True, null=True)
    # Slaicer models reference
    quote = models.ForeignKey(SliceJob, on_delete=models.CASCADE, null=True, blank=True)

    @property
    def completed_pieces(self):
        return len([p for p in self.unit_pieces.all() if p.success])

    @property
    def pending_pieces(self):
        return len([p for p in self.unit_pieces.all() if p.pending])

    @property
    def queued_pieces(self):
        return self.copies - self.completed_pieces - self.pending_pieces

    def get_deadline_from_now(self):
        return  (self.order.due_date - timezone.localdate()).total_seconds()

    def quote_ready(self):
        if self.stl is not None:
            return self.quote.ready()
        elif self.gcode is not None:
            return self.gcode.ready()

    def get_build_time(self):
        if not self.quote_ready():
            return None
        if self.stl is not None:
            return self.quote.build_time
        else:
            return self.gcode.build_time

    def get_weight(self):
        if not self.quote_ready():
            return None
        if self.stl is not None:
            return self.quote.weight
        else:
            return self.gcode.weight


@receiver(pre_save, sender=Piece)
def validate_piece(sender, instance, update_fields, **kwargs):
    # We need an STL or a Gcode, but not both
    if (instance.stl is None and instance.gcode is None) or (instance.stl is not None and instance.gcode is not None):
        raise ValidationError("Please set piece gcode OR stl")
    # We need at least a color and a material
    if len(instance.color.count()) == 0 or len(instance.material.count()) == 0:
        raise ValidationError("Please select at least a color and a material")


@receiver(post_save, sender=Piece)
def launch_piece_quoting_tasks(sender, instance, created, **kwargs):
    # We start quoting tasks
    if created:
        if instance.stl is not None:
            instance.stl.create_orientation_result()
            instance.stl.create_geometry_result()
            instance.quote = SliceJob.objects.quote_object(instance.stl)
            instance.save(update_fields=['quote'])
        if instance.gcode is not None:
            instance.gcode.celery_id = quote_gcode.s(instance.id).apply_async()
            instance.gcode.save(update_fields=['celery_id'])


class UnitPiece(models.Model):
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name='unit_pieces')
    job = models.ForeignKey('PrintJob', on_delete=models.CASCADE, related_name='unit_pieces')

    @property
    def pending(self):
        return self.job.pending

    @property
    def success(self):
        return self.job.success


# PrintJob Model

class PrintJob(models.Model):
    task = models.OneToOneField(OctoprintTask, on_delete=models.CASCADE, related_name='print_job')
    success = models.NullBooleanField()
    created = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    filament = models.ForeignKey(Filament, on_delete=models.CASCADE)

    @property
    def printing(self):
        return not self.task.ready

    @property
    def awaiting_for_bed_removal(self):
        return not self.printing and self.success is None

    @property
    def pending(self):
        return self.printing or self.awaiting_for_bed_removal

