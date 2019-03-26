from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings
from . import models as modelos
import trimesh
from .tools.orientation_optimization import generate_tweaker_result
from .tools.layer_height_optimization import LayerHeightOptimizer
import os
from django.core.files import File
import requests
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
    tr.model.rotation_matrix = tweaker_result.matrix.tolist()
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
        geometrymodel.geometry.plot = File(lho.plot_layers_profile())
        geometrymodel.geometry.save()
    else:
        # Well, we have to post the plot
        url = "{protocol}://{domain}{url}".format(**{'protocol': settings.CURRENT_PROTOCOL,
                                                     'domain': Site.objects.get_current().domain,
                                                     'url': reverse('slaicer:update_geometry_result', kwargs={'id':geometrymodel.geometry.id})})
        requests.post(url, files={'plot': lho.plot_layers_profile().open('rb')})



