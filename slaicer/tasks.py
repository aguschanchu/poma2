from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings
from . import models as modelos
import trimesh
from .tools.orientation_optimization import generate_tweaker_result


@shared_task()
def fill_tweaker_result(geometrymodel_id):
    geometrymodel = modelos.GeometryModel.objects.get(id=geometrymodel_id)
    # Returns a Tweak instance
    tweaker_result = generate_tweaker_result(geometrymodel)

    # Tenemos lo necesario, guardamos
    geometrymodel.orientation.unprintability_factor = tweaker_result.unprintability
    geometrymodel.orientation.rotation_matrix = tweaker_result.matrix.tolist()
    geometrymodel.orientation.save(update_fields=['unprintability_factor', 'rotation_matrix'])

    # Guardamos la geometria del objeto
    mesh = trimesh.load_mesh(geometrymodel.get_model_path())
    geometrymodel.orientation.size_x = mesh.bounding_box.primitive.extents[0]
    geometrymodel.orientation.size_y = mesh.bounding_box.primitive.extents[1]
    geometrymodel.orientation.size_z = mesh.bounding_box.primitive.extents[2]
    geometrymodel.orientation.save(update_fields = ['size_x', 'size_y', 'size_z'])

