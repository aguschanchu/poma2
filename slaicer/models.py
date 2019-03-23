from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from skynet.models import Material
import datetime
from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.sites.models import Site
from django.conf import settings
from .tools import slicer_profiles_helper
from . import tasks
import os
import string
import random
from celery.result import AsyncResult
from urllib3.util import Retry
from urllib3 import PoolManager, ProxyManager, Timeout
from urllib3.exceptions import MaxRetryError, TimeoutError


'''
Los siguientes modelos, corresponden a un los 3 settings requeridos por Slic3r para hacer un trabajo. A saber, parametros
de impresion, de filamento, y de impresora. El primero de estos, corresponde a un archivo ini (config-bundle de Slic3r)
donde estos perfiles están escritos.
Los parametros de sliceos indicados por la instancia (de haberlos), son priorizados por encima de los especificados en el 
archivo ini.
Algunas definiciones a tener en cuenta:
- PrinterProfile > base_quality: Es un numero que se utiliza como modificador de la calidad de la impresora, relativo a una MK3.
A mayor numero, significa que es una máquina peor. Por definicion, en el caso de una MK3 es 1. Por ejemplo, una CR10 es 
n 1,3, pues una 0,15 en una CR10 es en calidad similar a una MK3 en 0,2 (0,2/0,15 = 1,3)
'''

def get_connection_pool():
    retry_policy = Retry(total=5, backoff_factor=0.1, status_forcelist=list(range(405, 501)))
    timeout_policy = Timeout(read=10, connect=5)
    http = PoolManager(retries=retry_policy, timeout=timeout_policy)

    return http

class ConfigurationFile(models.Model):
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=10)
    vendor = models.CharField(max_length=300, null=True)
    # TODO: Proveer metodo para actualizar automaticamente. Usar sintaxis del repo de prusa3d
    provider = models.CharField(max_length=300, null=True, validators=[URLValidator])
    file = models.FileField(upload_to='slaicer/configuration_files/')

    def import_available_profiles(self):
        slicer_profiles_helper.import_available_profiles(self)


class PrinterProfile(models.Model):
    name = models.CharField(max_length=300)
    base_quality = models.FloatField(default=1)
    # config_name es el nombre que se utiliza en la configuracion referenciada
    config_name = models.CharField(max_length=200)
    config_file = models.ForeignKey(ConfigurationFile, on_delete=models.CASCADE)
    # guardamos todos los atributos que no nos interesan aca
    config = JSONField(null=True)


class MaterialProfile(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, null=True)
    config_name = models.CharField(max_length=200)
    config_file = models.ForeignKey(ConfigurationFile, on_delete=models.CASCADE)
    config = JSONField(null=True)


class PrintProfile(models.Model):
    layer_height = models.FloatField()
    fill_density = models.IntegerField(validators=[MaxValueValidator(100), MinValueValidator(0)])
    support_material = models.NullBooleanField()
    config_name = models.CharField(max_length=200)
    config_file = models.ForeignKey(ConfigurationFile, on_delete=models.CASCADE)
    config = JSONField(null=True)


'''
SliceConfiguration nuclea las instancias de los modelos anteriores, y se utiliza principalmente para definir los atributos
que desprenden de este.
'''


class SliceConfiguration(models.Model):
    printer = models.ForeignKey(PrinterProfile, on_delete=models.SET_NULL, null=True)
    material = models.ForeignKey(MaterialProfile, on_delete=models.SET_NULL, null=True)
    print = models.ForeignKey(PrintProfile, on_delete=models.SET_NULL, null=True)

    @property
    def print_quality(self):
        return self.printer.base_quality * self.print.layer_height

'''
Un archivo STL es la entrada requerida por el Slic3r. Consta de informacion de su orientabilidad
(que determina el soporte) y geometria (que determina su altura de capa)
'''


class TweakerResult(models.Model):
    unprintability_factor = models.FloatField(default=0, null=True)
    rotation_matrix = ArrayField(ArrayField(models.FloatField(), size=3), size=3, null=True)
    size_x = models.FloatField(blank=True,default=0)
    size_y = models.FloatField(blank=True,default=0)
    size_z = models.FloatField(blank=True,default=0)
    celery_id = models.CharField(max_length=50)
    # TODO: Discretizar errores posibles (Tweak)
    error_log = models.CharField(max_length=300, null=True)

    def ready(self):
        return AsyncResult(self.celery_id).ready()

class GeometryResult(models.Model):
    mean_layer_height = models.FloatField(default=0.15)
    plot = models.ImageField(upload_to='slaicer/plots/')
    celery_id = models.CharField(max_length=50)
    # TODO: Discretizar errores posibles (Geom)
    error_log = models.CharField(max_length=300, null=True)


class GeometryModel(models.Model):
    file = models.FileField(upload_to='slaicer/geometry/')
    orientation = models.OneToOneField(TweakerResult, on_delete=models.SET_NULL, null=True, blank=True)
    orientation_req = models.BooleanField(default=True)
    geometry = models.OneToOneField(GeometryResult, on_delete=models.SET_NULL, null=True, blank=True)
    geometry_req = models.BooleanField(default=True)
    scale = models.FloatField(default=1)

    # The worker may be running on a different server, so, we might need to fetch the model from the database server
    def get_model_path(self):
        if os.path.exists(self.file.path):
            return self.file.path
        else:
            # We need to download the file
            http = get_connection_pool()
            url = "{protocol}://{domain}{url}".format(**{'protocol': settings.CURRENT_PROTOCOL,
                                                         'domain': Site.objects.get_current().domain,
                                                         'url': self.file.url})
            path = "{base_dir}/tmp/{id}-{rand_string}.{extension}".format(**{'base_dir': settings.BASE_DIR,
                                                                             'id': self.id,
                                                                             'rand_string': ''.join(random.choice(string.ascii_letters) for m in range(10)),
                                                                             'extension': self.file.name.split('.')[-1]})

        with open(path, 'wb') as file:
            file.write(http.request('GET', url).data)
        return path


    def create_orientation_result(self):
        # Does the instance exists already?
        if not self.orientation is None:
            return None
        # Ok, no, lets create the task
        task = tasks.fill_tweaker_result.s(self.id).apply_async()
        self.orientation = TweakerResult.objects.create(celery_id=task.id)
        self.save(update_fields=['geometry'])



'''
Trabajo de sliceo. Acepta multiples STLs
 - weight: Peso de la impresion, en kg
 - build_time: Tiempo de impresion, en segundos
'''


class SliceJob(models.Model):
    # Especificacion de perfil
    profile = models.ForeignKey(SliceConfiguration, on_delete=models.SET_NULL, null=True)
    # Parametros de trabajo
    stl = models.ManyToManyField(GeometryModel)
    save_gcode = models.BooleanField(default=False)
    created = models.DateTimeField(default=datetime.datetime.now)
    celery_id = models.CharField(max_length=50)
    # TODO: Discretizar errores posibles (SliceJob)
    error_log = models.CharField(max_length=300, null=True)
    # Resultados de trabajo
    weight = models.FloatField(null=True)
    build_time = models.FloatField(null=True)
    gcode = models.FileField(upload_to='slaicer/gcode/')


'''
Modelos accesorios
'''


#Una configuracion puede tener muchos perfiles al pedo, que no se usan. Por eso, se almacenan en un estado intermedio, hasta que se importa
class AvailableProfile(models.Model):
    types = (
        ('print', 'Print profile'),
        ('filament', 'Material profile'),
        ('printer', 'Printer profile')
    )
    profile_type = models.CharField(choices=types, max_length=200)
    config_name = models.CharField(max_length=200)
    config_file = models.ForeignKey(ConfigurationFile, on_delete=models.CASCADE)

    def convert(self):
        slicer_profiles_helper.convert_available_profile_to_model(self)

