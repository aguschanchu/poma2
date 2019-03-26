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

    pass

class OctoprintTask(models.Model):
    task_types = (('command', 'Command'),
                  ('job', 'Print job'))
    celery_id = models.CharField(max_length=200, null=True)
    connection = models.ForeignKey('OctoprintConnection', on_delete=models.CASCADE, related_name='tasks')
    # Instead of just sending the command to octoprint, we'll wait until it finishes
    wait_for_completion = models.BooleanField(default=False)
    type = models.CharField(choices=task_types, default='job')
    objects = OctoprintTaskManager()

    @property
    def status(self):
        return AsyncResult(self.celery_id).state

    @property
    def ready(self):
        return AsyncResult(self.celery_id).ready()

class OctoprintJobStatus(models.Model):
    name = models.CharField(max_length=300, null=True)
    estimated_print_time = models.IntegerField(null=True)
    estimated_print_time_left = models.IntegerField(null=True)

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
    job = models.OneToOneField(OctoprintJobStatus, on_delete=models.CASCADE)

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

    def _get_connection_headers(self):
        return {'x-api-key': self.apikey}

    def _issue_command(self, command: str):
        r = self._get_connection_pool().request('POST', urljoin(self.url, 'api/printer/command'),
                                                headers=self._get_connection_headers(),
                                                fields={'command': command})
        if r.status == 204:
            return True
        else:
            raise MaxRetryError("Error sending command to instance")

    def _print_file(self):
        pass

    # Check if octoprint API url is valid
    def ping(self):
        r = json.loads(self._get_connection_pool().request('GET', urljoin(self.url, 'api/version'),
                                                           headers=self._get_connection_headers()).data.decode('utf-8'))
        if r.status == 200:
            return True
        else:
            return False

    def update_status(self):
        try:
            r = json.loads(self._get_connection_pool().request('GET', urljoin(self.url, 'api/printer'),
                                                               headers=self._get_connection_headers()).data.decode('utf-8'))
            OctoprintStatus.objects.filter(octoprintconnection=self).update(**r['state']['flags'])
            r = json.loads(self._get_connection_pool().request('GET', urljoin(self.url, 'api/job'),
                                                               headers=self._get_connection_headers()).data.decode('utf-8'))
            self.status.job.name = r['job']['file']['name']
            self.status.job.estimated_print_time = r['job']['estimatedPrintTime']
            self.status.job.estimated_print_time_left = r['progress']['printTimeLeft']
            self.status.job.save()
        except:
            self.status.connectionError = True
        self.status.last_update = timezone.now
        self.status.save()

@receiver(pre_save, sender=OctoprintConnection)
def validate_octoprint_connection_on_creation(sender, instance, update_fields, **kwargs):
    # No update_fields were specified, so, probably it's a new instance
    if not update_fields:
        if not instance.ping():
            raise ValidationError("Error on connecting to octoprint instance")

@receiver(post_save, sender=OctoprintStatus)
def create_octoprint_state(sender, instance, created, **kwargs):
    if created:
        o = OctoprintJobStatus.objects.create()
        instance.job = o
        instance.save()

@receiver(post_save, sender=OctoprintConnection)
def create_octoprint_job_state(sender, instance, created, **kwargs):
    if created:
        o = OctoprintStatus.objects.create()
        instance.status = o
        instance.save()




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

