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
import csv
import subprocess
import re
from django.core.files.base import ContentFile

class ModelNotReady(Exception):
    """Model not ready exception, used for celery autoretry"""
    pass

@shared_task(queue='celery', autoretry_for=(ModelNotReady,), max_retries=5, default_retry_delay=2)
def fill_tweaker_result(geometrymodel_id):
    try:
        geometrymodel = modelos.GeometryModel.objects.get(id=geometrymodel_id)
    except modelos.GeometryModel.DoesNotExist:
        raise ModelNotReady
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


@shared_task(queue='celery', autoretry_for=(ModelNotReady,), max_retries=5, default_retry_delay=2)
def fill_geometry_result(geometrymodel_id):
    try:
        geometrymodel = modelos.GeometryModel.objects.get(id=geometrymodel_id)
    except modelos.GeometryModel.DoesNotExist:
        raise ModelNotReady

    # Returns a LayerHeightOptimizer instance
    lho = LayerHeightOptimizer.import_from_geometrymodel(geometrymodel)
    lho.create_layer_profile()
    geometrymodel.geometry.mean_layer_height = lho.calculate_layer_height()
    geometrymodel.geometry.save()

    # Lets save the layer profile plot
    if os.path.exists(geometrymodel.file.path):
        geometrymodel.geometry.plot.save('plot.jpg', File(lho.plot_layers_profile()))
        geometrymodel.geometry.save()
    else:
        # Well, we have to post the plot
        url = "{protocol}://{domain}{url}".format(**{'protocol': settings.CURRENT_PROTOCOL,
                                                     'domain': Site.objects.get_current().domain,
                                                     'url': reverse('slaicer:update_geometry_result',
                                                                    kwargs={'id': geometrymodel.geometry.id})})
        requests.post(url, files={'plot': lho.plot_layers_profile().open('rb')})


def parse_weight(line):
    return float(re.split('= ', line)[1])


def parse_build_time(line):
    line = re.split('=', line)[1]
    if 'd' in line:
        output_slic3r = re.split('[dhms]', line)
        # Time to seconds conversion
        printing_time_s = int(output_slic3r[0]) * 24 * 60 ** 2 + int(output_slic3r[1]) * 60 ** 2 + int(
            output_slic3r[2]) * 60 + int(output_slic3r[3])
    elif 'h' in line:
        output_slic3r = re.split('[hms]', line)
        printing_time_s = int(output_slic3r[0]) * 60 ** 2 + int(output_slic3r[1]) * 60 + int(output_slic3r[2])
    elif 'm ' in line:
        output_slic3r = re.split('[ms]', line)
        printing_time_s = int(output_slic3r[0]) * 60 + int(output_slic3r[1])
    else:
        output_slic3r = re.split('s', line)
        printing_time_s = int(output_slic3r[0])
    return printing_time_s




@shared_task(queue='celery', autoretry_for=(ModelNotReady,), max_retries=60, default_retry_delay=2)
def slice_model(slicejob_id):
    try:
        slicejob = modelos.SliceJob.objects.get(id=slicejob_id)
    except modelos.SliceJob.DoesNotExist:
        raise ModelNotReady
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
        mesh.apply_transform(rotation_matrix)
        # Do we need to rescale the model?
        if obj.scale != 1.0:
            mesh.apply_transform(trimesh.transformations.scale_matrix(obj.scale, [0, 0, 0]))
        # Save rotated model
        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        path = os.path.join(settings.BASE_DIR, 'tmp', rand_str + '.stl')
        with open(path, 'wb') as f:
            f.write(trimesh.exchange.stl.export_stl(mesh))
        models_path.append(path)

    # Profile configuration
    if slicejob.profile.auto_print_profile:
        # We need to choose a profile based on GeometryResult, if it wasn't specified by user
        min_layer_height = min([m.geometry.mean_layer_height for m in models]) / slicejob.profile.printer.base_quality
        print_profiles_available = slicejob.profile.printer.available_print_profiles.all()
        recommended_quality = min([p.layer_height for p in print_profiles_available],
                                  key=lambda x: abs(x - min_layer_height))
        slicejob.profile.print = print_profiles_available.filter(layer_height=recommended_quality)[0]

    if slicejob.profile.auto_support:
        support_needed = any([m.orientation.support_needed for m in models])
        slicejob.profile.print.support_material = support_needed

    slicejob.profile.save()

    # All set, we write the configuration to a ini file
    rand_str = ''.join(random.choice(string.ascii_letters) for m in range(10))
    ini_path = os.path.join(settings.BASE_DIR, 'tmp/', rand_str + '.ini')
    output_path = os.path.join(settings.BASE_DIR, 'tmp/', rand_str + '.gcode')
    full_config = {**slicejob.profile.print.get_dict(), **slicejob.profile.printer.get_dict(),
                   **slicejob.profile.material.get_dict()}
    with open(ini_path, 'w') as f:
        writer = csv.writer(f, delimiter='=', )
        for key, value in full_config.items():
            writer.writerow([key, value])

    # We launch Slic3r using subprocess
    slic3r_bin_dir = os.path.join(settings.BASE_DIR, 'slaicer/lib/Slic3r/slic3r.pl')
    if not os.path.exists(slic3r_bin_dir):
        raise modelos.LibrariesNotConfigured
    print([slic3r_bin_dir, '--load', ini_path, '-m', '-o', output_path, *models_path])
    proc = subprocess.run([slic3r_bin_dir, '--load', ini_path, '-o', output_path, *models_path],
                          universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout.splitlines():
        if 'Done' in line:
            # We search for print time in the output
            proc = subprocess.run(['tail', output_path, '-n', '500'], universal_newlines=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            for line in proc.stdout.splitlines():
                if 'estimated printing time (normal mode)' in line:
                    slicejob.build_time = parse_build_time(line)
                elif 'filament used' in line and 'cm' not in line:
                    slicejob.weight = parse_weight(line)
            slicejob.save(update_fields=['build_time', 'weight'])
            # We save the gcode
            if slicejob.save_gcode:
                with open(output_path, 'rb') as f:
                    slicejob.gcode.save('model.gcode', ContentFile(f.read()))
            # Temp files cleaning
            os.remove(ini_path)
            os.remove(output_path)
            return True
    # Slicer didn't finish correctly
    else:
        slicejob.error_log = proc.stderr
        print(proc.stderr)
        print(proc.stdout)
        slicejob.save(update_fields=['error_log'])
        return False
