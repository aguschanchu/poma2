import sys
import os
from time import time
import importlib.util
import trimesh
from django.conf import settings
import random, string
from django.apps import apps
import logging

'''
Esta funcion ejecuta el mismo orientador que usa Cura, y se puede encontrar aca: https://github.com/ChristophSchranz/Tweaker-3/
Considera la orientacion de impresion más factible. Asimismo, sugiere o no el uso de soporte via el parametro "Unprintability"
'''

def generate_tweaker_result(geometrymodel):
    # Cargamos Tweaker3. Este bardo es porque no esta en el directorio donde corre el script
    spec = importlib.util.spec_from_file_location('Tweak', settings.BASE_DIR + '/slaicer/lib/Tweaker-3/MeshTweaker.py')
    Tweaker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(Tweaker)
    spec = importlib.util.spec_from_file_location('ThreeMF', settings.BASE_DIR + '/slaicer/lib/Tweaker-3/ThreeMF.py')
    ThreeMF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ThreeMF)
    try:
        spec = importlib.util.spec_from_file_location('FileHandler', settings.BASE_DIR + '/slaicer/lib/Tweaker-3/FileHandler.py')
        FileHandler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(FileHandler)
    except ModuleNotFoundError:
        raise ValueError("Error importing FileHandler. Please remove the ThreeMF import line from slaicer/lib/Tweaker-3/FileHandler.py")

    try:
        path = geometrymodel.file.path
        FileHandlerInstance = FileHandler.FileHandler()
        objs = FileHandlerInstance.load_mesh(path)
        if objs is None:
            raise ValueError
    except(KeyboardInterrupt, SystemExit, ValueError):
        # Hubo un error al cargar el archivo, intentamos pasarlo por trimesh previamente
        mesh = trimesh.load_mesh(path)
        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        path = settings.BASE_DIR + '/tmp/' + rand_str + '.stl'
        with open(path, 'wb') as f:
            f.write(trimesh.exchange.stl.export_stl(mesh))
        FileHandlerInstance = FileHandler.FileHandler()
        objs = FileHandlerInstance.load_mesh(path)

    # Una vez con el STL cargado, ejecutamos el optimizador

    tweaker_settings = {
        'extended_mode' : True,
        'verbose' : False,
        'show_progress':  False,
        'favside': None,
        'volume': None
    }
    info = dict()
    if len(objs.items()) > 1:
        logging.warning("Multiple parts detected, this shouldn't happen")
    for part, content in objs.items():
        mesh = content["mesh"]
        info[part] = dict()
        try:
            cstime = time()
            x = Tweaker.Tweak(mesh,
                              tweaker_settings['extended_mode'],
                              tweaker_settings['verbose'],
                              tweaker_settings['show_progress'],
                              tweaker_settings['favside'],
                              tweaker_settings['volume'])
            info[part]["matrix"] = x.matrix
            info[part]["tweaker_stats"] = x

            # Tenemos lo necesario, guardamos
            tweaker_result = geometrymodel.orientation
            tweaker_result.unprintability_factor = x.unprintability
            tweaker_result.rotation_matrix = x.matrix.tolist()
            tweaker_result.save(update_fields=['unprintability_factor', 'rotation_matrix'])

        except (KeyboardInterrupt, SystemExit):
            raise SystemExit("\nError, tweaking process failed!")

    # Guardamos la geometria del objeto
    tweaker_result = geometrymodel.orientation
    mesh = trimesh.load_mesh(geometrymodel.file.path)
    tweaker_result.size_x = mesh.bounding_box.primitive.extents[0]
    tweaker_result.size_y = mesh.bounding_box.primitive.extents[1]
    tweaker_result.size_z = mesh.bounding_box.primitive.extents[2]
    tweaker_result.save(update_fields = ['size_x', 'size_y', 'size_z'])


