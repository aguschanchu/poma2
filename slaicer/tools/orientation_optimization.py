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
        path = geometrymodel.get_model_path()
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
        'extended_mode': True,
        'verbose': False,
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

        except (KeyboardInterrupt, SystemExit):
            raise SystemExit("\nError, tweaking process failed!")
    return x




