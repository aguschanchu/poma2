from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
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

'''
OctoprintConnection handles API endpoints with octoprint
'''

class OctoprintTaskManager(models.Manager):
    def create_task(self, connection, commands=None, file=None):
        # It's a valid task?
        if file is None and commands is None or commands is not None and file is not None:
            raise ValidationError("Please specify a command or a file")
        if file is not None:
            file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + '.gcode'
            o = self.create(type='job', connection=connection)
            o.file.save(file_name, file)
        else:
            # So, it's a command task. Before, we check if the object received is a file, or just a string
            if hasattr(commands, 'open'):
                commands = commands.open('r').read()
            o = self.create(type='command', commands=commands, connection=connection)
        return o


class OctoprintTask(models.Model):
    task_types = (('command', 'Command'),
                  ('job', 'Print job'))
    celery_id = models.CharField(max_length=200, null=True)
    connection = models.ForeignKey('OctoprintConnection', on_delete=models.CASCADE, related_name='tasks')
    type = models.CharField(choices=task_types, default='job', max_length=200)
    # Accepts multiple commands, separated each one with a newline ('\n')
    commands = models.TextField(null=True)
    file = models.FileField(null=True)
    # Used to track task status
    job_sent = models.BooleanField(default=False)
    job_filename = models.CharField(max_length=300, null=True)
    objects = OctoprintTaskManager()

    @property
    def status(self):
        if self.celery_id is None:
            return 'PENDING'
        else:
            return AsyncResult(self.celery_id).state

    @property
    def ready(self):
        if self.celery_id is None:
            return False
        else:
            return AsyncResult(self.celery_id).ready()


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

    @property
    def instance_ready(self):
        return self.ready and not self.connectionError


class OctoprintConnection(models.Model):
    url = models.CharField(max_length=300, validators=[URLValidator(schemes=['http', 'https'])])
    apikey = models.CharField(max_length=200)
    active_task = models.ForeignKey(OctoprintTask, on_delete=models.SET_NULL, null=True)
    # If the connection is locked, no new tasks will be executed from the queue.
    locked = models.BooleanField(default=False)
    # Octoprint flags
    status = models.OneToOneField(OctoprintStatus, null=True, on_delete=models.CASCADE)

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
            file_content = f.read() + 'M400 \nM115'
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
            OctoprintStatus.objects.filter(octoprintconnection=self).update(**r['state']['flags'], connectionError = False)
            self.refresh_from_db()
            if 'temperature' in r.keys():
                self.status.temperature.tool = r['temperature'].get('tool0')
                self.status.temperature.bed = r['temperature'].get('bed')
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

    def create_task(self, commands=None, file=None):
        return OctoprintTask.objects.create_task(self, commands=commands, file=file)


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
                                           temperature=OctoprintTemperature.objects.create())
        instance.status = o
        instance.save()
        # Status update scheduling
        # TODO: Modify update period accordingly to task
        schedule, created = IntervalSchedule.objects.get_or_create(every=2, period=IntervalSchedule.SECONDS)
        PeriodicTask.objects.create(interval=schedule,
                                    name='Update OctoprintConnection id {}'.format(instance.id),
                                    task='skynet.tasks.update_octoprint_status',
                                    kwargs=json.dumps({'conn_id': instance.id}))

# Printer Model

class Printer(models.Model):
    name = models.CharField(max_length=200)
    uuid = models.IntegerField()
    printer_type = models.ForeignKey(PrinterType, on_delete=models.CASCADE)
    connection = models.OneToOneField(OctoprintConnection, related_name='source', on_delete=models.CASCADE)
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

