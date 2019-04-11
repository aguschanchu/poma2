# Various tasks for PoMa 2
from __future__ import absolute_import, unicode_literals
from celery import shared_task, group
import skynet.models as skynet_models
from datetime import datetime, timedelta
from math import pi
import os
import subprocess
from slaicer.tasks import parse_build_time
from django.conf import settings
import traceback

@shared_task(queue='celery')
def quote_gcode(piece_id):
    """
    Quotes a single gcode to obtain the estimated printing time and weight.
    """
    piece = skynet_models.Piece.objects.get(id=piece_id)
    # Reads printing time from gcode file.
    filename = os.path.join(settings.BASE_DIR, piece.gcode.print_file.path)

    supported_slicers = {'Slic3r': slicer_parser,
                         'Simplify3D': simplify_parser,
                         'Cura': cura_parser}

    # TODO Implement this for other Slicing programs (Slimpify3D, Cura, etc)
    # Determine which Slicing program was used.
    head = subprocess.check_output("head -5 "+filename, shell=True).decode("utf-8").split("\n")
    for slicing_program in supported_slicers.keys():
        if any([slicing_program in line for line in head]):
            try:
                time, length = supported_slicers[slicing_program](filename)
            except:
                traceback.print_exc()
                time, length = timedelta(hours=20), 0
            radius = (1.75 / 2) / 10  # in cm
            density = piece.material.density
            weight_g = radius ** 2 * pi * length * density  # in g
            weight_kg = weight_g / 1000  # in kg

            piece.gcode.build_time = time.total_seconds()
            piece.gcode.weight = weight_g
            print(time.total_seconds(), weight_g)
            piece.gcode.save(update_fields=['build_time', 'weight'])
            return True


def slicer_parser(filename):
    """ Parser that reads the estimated printing time for gcodes that were
    sliced with Slic3r. """
    # Find last lines of the file
    lines = subprocess.check_output("tail -500 "+filename, shell=True).decode("utf-8").split("\n")

    for line in lines:
        if 'estimated printing time (normal mode)' in line:
            seconds = parse_build_time(line)
        if "filament used" in line:
            length_str = line.split(" = ")[1]

    dt = timedelta(seconds=seconds)

    # Get length
    length = float(length_str.split("mm")[0]) / 10  # in cm

    return dt, length


def simplify_parser(filename):
    """ Parser that reads the estimated printing time for gcodes that were
    sliced with Simplify3D. """

    lines = subprocess.check_output(
        "tail -5 "+filename, shell=True).decode("utf-8").split("\n")

    time_str = ""
    length_str = ""
    dt = timedelta(hours=25)  # Default printing time
    length = 1000

    for line in lines:
        if "Build time" in line:
            time_str = line.split(": ")[1]
        if "Filament length" in lines:
            length_str = line.split(": ")[1]

    # Parse the printing time
    if 'hours' in time_str:
        # Piece takes more than 2 hours, hence the "hours" plural
        time_split = time_str.split(" hours ")
    else:
        # Piece takes less than 2 hours, hence the "hour" singular
        time_split = time_str.split(" hour ")
    hours = int(time_split[0]) if len(time_split) > 1 else 0
    print(time_split)
    time_str = time_split[1] if len(time_split) > 1 else time_split[0]
    print(time_str)
    # Same with minutes
    if 'minutes' in time_str:
        # Piece takes more than 2 hours, hence the "hours" plural
        time_split = time_str.split(" minutes")
    else:
        # Piece takes less than 2 hours, hence the "hour" singular
        time_split = time_str.split(" minute")
    minutes = int(time_split[0]) if len(time_split) > 1 else 0
    dt = timedelta(hours=hours, minutes=minutes)


    # Parse weight of the piece
    try:
        length = float(length_str.split(" mm ")[0]) / 10  # in cm
    except:
        pass

    return dt, length


def cura_parser(filename):
    """ Parser that reads the estimated printing time for gcodes that were
    sliced with Cura. """

    lines = subprocess.check_output(
        "head -5 "+filename, shell=True).decode("utf-8").split("\n")

    # Default values
    dt = timedelta(hours=25)
    length = 1000

    for line in lines:
        if "TIME" in line:
            try:
                seconds = int(line.split(":")[1])
                dt = timedelta(seonds=seconds)
            except:
                pass
        if "Filament used" in line:
            try:
                length = float(line.split(": ")[1].split("m")[0]) * 100
            except:
                pass

    return dt, length


'''
OctoprintConnection Celery tasks
'''

class PrintNotFinished(Exception):
   """Print not finished exception, used for celery autoretry"""
   pass


@shared_task(queue='celery', autoretry_for=(PrintNotFinished,), max_retries=None, default_retry_delay=2)
def send_octoprint_task(task_id):
    """ 
    Sends OctoprintTask to printer. In case we need to wait for completion, the task will keep raising PrintNotFinished
    exception, until the print finishes. Please don't send printjobs using this task. Instead, use OctoprintTask
    object manager
    """
    task = skynet_models.OctoprintTask.objects.get(pk=task_id)
    # type: command
    if task.type == 'command':
        task.job_sent = True
        task.save()
        return task.connection._issue_command(task.commands)
    # type: job
    ## Let's send the job
    if not task.job_sent:
        t = task.connection._print_file(task.file)
        if t is not None:
            task.job_sent = True
            task.job_filename = t
            task.save()
            task.connection.update_status()
    ## The printer should be working by now. Let's check for job completion
    if not task.job_filename == task.connection.status.job.name:
        raise ValueError("Incorrect job name. Printer was manually controlled, so, we lost job tracking")
    if task.connection.status.printing:
        raise PrintNotFinished
        print("Printing")
    else:
        return True


@shared_task(queue='celery')
def update_octoprint_status(conn_id):
    connection = skynet_models.OctoprintConnection.objects.get(pk=conn_id)
    connection.update_status()


@shared_task(queue='celery')
def octoprint_task_dispatcher():
    """
    Checks for pending OctoprintTasks on each connection, and starts the task
    """
    for conn in skynet_models.OctoprintConnection.objects.all():
        # Update current task
        if conn.active_task is not None:
            if conn.active_task.ready and conn.active_task.awaiting_for_human_intervention:
                # We clear the current task
                conn.active_task = None
        # Send new task
        if conn.active_task is None and conn.connection_ready:
            # Do we have pending tasks?
            if conn.tasks.filter(celery_id=None).exists():
                t = conn.tasks.filter(celery_id=None).first()
                # Mark task as active
                conn.active_task = t
                conn.save()
                # Send task to celery queue
                ct = send_octoprint_task.delay(t.id)
                t.celery_id = ct.id
                t.save()



