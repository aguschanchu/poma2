import os
import re
import configparser
import logging
import csv
# Para la eleccion de los nombres de los gcode
import string
import random
from django.conf import settings
from typing import List
from django.apps import apps
import traceback

'''
Este archivo contiene la rutina para importar un archivo de configuracion.
Al crear un ConfigurationFile (subiendo su respectivo file) busca todos los perfiles
validos que este ofrece, y los carga a la db (PrintProfile, entre otros).
'''


# Cargamos el archivo de configuracion
def load_configuration_from_model(conf) -> configparser.ConfigParser:
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read(conf.file.path)
        return config
    except configparser.MissingSectionHeaderError:
        raise ValueError("El archivo de configuracion es invalido. Revisar que se trate de un ini bien formateado")
    except:
        # TODO: Restringir errores del ConfigParser
        raise ValueError("Error al leer archivo de configuracion")


# Cuales son los perfiles validos para cada categoria
def get_profiles_available(conf) -> List:
    config = load_configuration_from_model(conf)
    ans = {'print': [], 'filament': [], 'printer': []}
    for element in config.sections():
        if len(re.split(':', element)) == 2:
            type = re.split(':', element)[0]
            name = re.split(':', element)[1]
        else:
            type = None
            name = None
        if type == 'print':
            ans['print'].append(name)
        elif type == 'filament':
            ans['filament'].append(name)
        elif type == 'printer':
            ans['printer'].append(name)
    return ans


# Algunas categorias dependen de otras. La idea, es devolver un diccionario con todas las propiedades de esa categoria, sin dependencias
def get_full_configuration(conf, category: str) -> dict:
    config = load_configuration_from_model(conf)
    perfil = {}
    if "inherits" in config.options(category):
        # Levantamos la dependencia y buscamos la config
        for dependence in config[category]["inherits"].split("; "):
            # En que seccion nos fijamos?
            section = category.split(":")[0]
            if "inherits" in config.options(section + ":" + dependence):
                perfil = perfil.copy()
                perfil.update(get_full_configuration(conf, section + ":" + dependence))
            for opcion in config.options(section + ":" + dependence):
                perfil[opcion] = config[section + ":" + dependence][opcion]
    for opcion in config.options(category):
        perfil[opcion] = config[category][opcion]
    # Es un modelo de impresora? Tal vez tenga informacion en la categoria del modelo
    if 'printer_model' in config.options(category):
        dependence = "printer_model:" + config[category]["printer_model"]
        if dependence in config.sections():
            for opcion in config.options(dependence):
                perfil[opcion] = config[dependence][opcion]
    return perfil


# Actualizamos los perfiles de impresion de cada PrintProfile basado en la compatibilidad especificada en el ini
def get_compatible_printers_condition(print_profile):
    conditions = print_profile.get_compatible_printers_condition().split(' and ')
    filtered_conditions = {}
    for condition in conditions:
        s = re.search(re.escape('printer_notes=~/.*')+'(.*)'+re.escape('.*/'), condition)
        if s is not None:
            s = s.group(1)
            # Is a printer model condition?
            if 'PRINTER_MODEL' in s:
                filtered_conditions['printer_model'] = s.split('PRINTER_MODEL_')[1]
        # Is a nozzle diameter condition?
        elif 'nozzle_diameter' in condition:
            filtered_conditions['nozzle_diameter'] = float(condition.split('nozzle_diameter[0]==')[1])
    PrinterProfile = apps.get_model('slaicer.PrinterProfile')
    return PrinterProfile.objects.filter(**filtered_conditions)


# Creamos el modelo PrinterProfile, a partir de un archivo de configuracion y una categoria (config_name)
def import_printer_profile(conf, category: str):
    cat_config = get_full_configuration(conf, 'printer:' + category)
    PrinterProfile = apps.get_model('slaicer.PrinterProfile')
    if PrinterProfile.objects.filter(config_name=category, config_file=conf).exists():
        p = PrinterProfile.objects.filter(config_name=category, config_file=conf)[0]
    else:
        p = PrinterProfile()
        p.config_name = category
        p.config_file = conf

    # Este campo es medio raro porque hay que acceder a otra seccion.
    p.name = cat_config.pop('name') if 'name' in cat_config.keys() else cat_config['printer_model']
    p.base_quality = cat_config.pop('base_quality') if 'base_quality' in cat_config.keys() else 1
    p.nozzle_diameter = cat_config.pop('nozzle_diameter') if 'nozzle_diameter' in cat_config.keys() else 0.4
    p.printer_model = cat_config.pop('printer_model')
    bed_shape = [a.split('x') for a in cat_config.pop('bed_shape').split(',')]
    if len(bed_shape) != 4:
        # Probably a invalid config was specified
        p.bed_shape = [200, 200, 200]
    else:
        p.bed_shape = [bed_shape[2][0], bed_shape[2][1], cat_config.pop('max_print_height') if 'max_print_height' in cat_config.keys() else 200]
    p.config = cat_config
    p.save()
    return p

# Idem anterior con Print Profile
def import_print_profile(conf, category: str):
    cat_config = get_full_configuration(conf, 'print:' + category)
    PrintProfile = apps.get_model('slaicer.PrintProfile')
    if PrintProfile.objects.filter(config_name=category, config_file=conf).exists():
        p = PrintProfile.objects.filter(config_name=category, config_file=conf)[0]
    else:
        p = PrintProfile()
        p.config_name = category
        p.config_file = conf

    p.layer_height = cat_config.pop('layer_height')
    p.fill_density = cat_config.pop('fill_density').split('%')[0]
    p.support_material = cat_config.pop('support_material') == '1' if 'support_material' in cat_config.keys() else 0
    p.config = cat_config
    p.save()
    p.add_compatible_printers()
    return p

# Idem anterior material
def import_material_profile(conf, category: str):
    cat_config = get_full_configuration(conf, 'filament:' + category)
    MaterialProfile = apps.get_model('slaicer.MaterialProfile')
    if MaterialProfile.objects.filter(config_name=category, config_file=conf).exists():
        p = MaterialProfile.objects.filter(config_name=category, config_file=conf)[0]
    else:
        p = MaterialProfile()
        p.bed_temperature = cat_config.pop('bed_temperature') if 'bed_temperature' in cat_config.keys() else 55
        p.nozzle_temperature = cat_config.pop('nozzle_temperature') if 'nozzle_temperature' in cat_config.keys() else 200
        p.config_name = category
        p.config_file = conf

    p.config = cat_config
    p.save()
    return p


# Importar todos los perfiles
def import_all_configurations(conf):
    profiles_availables = get_profiles_available(conf)

    for ps in profiles_availables['printer']:
        import_printer_profile(conf, ps)

    for ps in profiles_availables['print']:
        import_print_profile(conf, ps)

    for ps in profiles_availables['filament']:
        import_material_profile(conf, ps)


# Importar un perfil disponible a una configuacion
def convert_available_profile_to_model(aconf):
    if aconf.profile_type == 'print':
        import_print_profile(aconf.config_file, aconf.config_name)
    elif aconf.profile_type == 'printer':
        import_printer_profile(aconf.config_file, aconf.config_name)
    elif aconf.profile_type == 'filament':
        import_material_profile(aconf.config_file, aconf.config_name)


# Creamos todos los AvailableProfile de una configuracion
def import_available_profiles(conf):
    profiles_availables = get_profiles_available(conf)
    AvailableProfile = apps.get_model('slaicer.AvailableProfile')

    for profile_type in profiles_availables.keys():
        for name in profiles_availables[profile_type]:
            p = AvailableProfile.objects.get_or_create(profile_type=profile_type, config_name=name, config_file=conf)[0]
            p.save()

