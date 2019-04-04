from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings
from . import models as modelos
import numpy as np
import trimesh
from .tools.orientation_optimization import generate_tweaker_result
from .tools.layer_height_optimization import LayerHeightOptimizer
import os
from django.core.files import File
import random, string
from django.urls import reverse
from django.contrib.sites.models import Site
import requests


@shared_task()
def fill_tweaker_result(geometrymodel_id):
    geometrymodel = modelos.GeometryModel.objects.get(id=geometrymodel_id)
    # Returns a Tweak instance
    tweaker_result = generate_tweaker_result(geometrymodel)
    mesh = trimesh.load_mesh(geometrymodel.get_model_path())
    tr = geometrymodel.orientation

    # Tenemos lo necesario, guardamos
    tr.unprintability = tweaker_result.unprintability
    tr.rotation_matrix = tweaker_result.matrix.tolist()
    tr.size_x = mesh.bounding_box.primitive.extents[0]
    tr.size_y = mesh.bounding_box.primitive.extents[1]
    tr.size_z = mesh.bounding_box.primitive.extents[2]
    tr.save()


@shared_task()
def fill_geometry_result(geometrymodel_id):
    geometrymodel = modelos.GeometryModel.objects.get(id=geometrymodel_id)

    # Returns a LayerHeightOptimizer instance
    lho = LayerHeightOptimizer.import_from_geometrymodel(geometrymodel)
    lho.create_layer_profile()
    geometrymodel.geometry.mean_layer_height = lho.calculate_layer_height()
    geometrymodel.geometry.save()

    # Lets save the layer profile plot
    if os.path.exists(geometrymodel.file.path):
        geometrymodel.geometry.plot.save('plot.jpg',File(lho.plot_layers_profile()))
        geometrymodel.geometry.save()
    else:
        # Well, we have to post the plot
        url = "{protocol}://{domain}{url}".format(**{'protocol': settings.CURRENT_PROTOCOL,
                                                     'domain': Site.objects.get_current().domain,
                                                     'url': reverse('slaicer:update_geometry_result', kwargs={'id':geometrymodel.geometry.id})})
        requests.post(url, files={'plot': lho.plot_layers_profile().open('rb')})


class ModelNotReady(Exception):
   """Model not ready exception, used for celery autoretry"""
   pass


@shared_task(queue='celery', autoretry_for=(ModelNotReady,), max_retries=60, default_retry_delay=2)
def slice_model(slicejob_id):
    slicejob = modelos.SliceJob.objects.get(id=slicejob_id)
    models = slicejob.geometry_models.all()

    # Are all the models ready?
    for obj in models:
        if obj.orientation_req and not obj.orientation_result_ready:
            raise ModelNotReady
        if obj.geometry_req and not obj.geometry_result_ready:
            raise ModelNotReady

    # Model orientation
    models_path = []
    for obj in models:
        mesh = trimesh.load(obj.get_model_path())
        euler_angles = trimesh.transformations.euler_from_matrix(np.array(obj.orientation.rotation_matrix), 'rxyz')
        rotation_matrix = trimesh.transformations.euler_matrix(*euler_angles, 'rxyz')
        mesh.apply_transformation(rotation_matrix)
        # Save rotated model
        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        path = settings.BASE_DIR + '/tmp/' + rand_str + '.stl'
        with open(path, 'wb') as f:
            f.write(trimesh.exchange.stl.export_stl(mesh))
        models_path.append(path)

    # Profile configuration
    ## We need to choose a profile based on GeometryResult, if it wasn't specified by user





