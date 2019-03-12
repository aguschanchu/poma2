# Various tasks for PoMa 2

from .models import Piece, Order, Printer, Filament
from datetime import datetime, timedelta
from math import pi


def quote_order(order):
    """ 
    Funtion that quotes each piece of the order.
    """
    # Get all pieces of an order
    pieces = order.pieces.all()

    # Quote them one by one
    for piece in pieces:
        quote_piece(piece)

    return


def quote_piece(piece):
    """
    Quotes a single piece to obtain the estimated printing time and weight.
    """

    # If the piece contains an stl file then it has to be sent to the slAIcer API
    if piece.stl:

        # Create data and files dictionaries
        data = {'material': piece.filament.material.name,
                'calidad': piece.quality,
                'prioridad': piece.priority,
                'escala': piece.scale,
                # 'slicer_args': piece.slicer_args,
                }
        files = {'file': open(settings.BASE_DIR + piece.stl.url, 'rb')}

        # Tries to connect with the SlAIcer API and qoute the piece
        try:
            r = requests.post(settings.SLICERAPI, files=files, data=data)
            slicer_id = r.json()['id']
            for _ in range(0, 30):
                r = requests.get(settings.SLICERAPI + f'status/{slicer_id}/')
                if r.json()['estado'] == '200':
                    # If slicejob finished succesfully just get all the data
                    # Estimated printint time
                    piece.time = timedelta(seconds=r.json()['tiempo_estimado'])
                    # TODO Determine if we need to save size of piece
                    # piece.size_x = r.json()['size_x']
                    # piece.size_y = r.json()['size_y']
                    # piece.size_z = r.json()['size_z']

                    # TODO Check if object enters in one of the available printers
                    # impresoras = Impresora.objects.all()
                    # fits = True
                    # for imp in impresoras:
                    #     if piece.size_x <= imp.tam_x and piece.size_y <= imp.tam_y and piece.size_z <= imp.tam_z:
                    #         fits = True
                    #         break
                    # if fits:
                    #     piece.estado = '101'
                    # else:
                    #     piece.estado = '304'
                    # break

                # TODO Error Management if there is a problem with the slicing.
                # elif r.json()['estado'] in ('303', '304', '305'):
                #     # Si hubo un error al slicear cambia el estado del piece
                #     piece.estado = r.json()['estado']
                #     piece.save()
                #     return False
                # elif r.json()['estado'] in ('301', '302', '306'):
                #     # Estos son errores de slicero no relevantes al piece en si
                #     piece.estado = '301'
                #     piece.save()
                #     return False

                time.sleep(1)

            piece.save()  # Guarda los datos en la DB
            return True

    # If the piece conatins a gcode file, then it has to be parsed to find the
    # estimated printing time
    if piece.gcode:
        # Reads printing time from gcode file.
        filename = settings.BASE_DIR + piece.gcode.print_file.url

        supported_slicers = [("Slic3r", slicer_parser),
                             ("Simplify3D", simplify_parser),
                             ("Cura", cura_parser)]
        # TODO Implement this for other Slicing programs (Slimpify3D, Cura, etc)
        # Determine which Slicing program was used.
        slicer = ""
        head = subprocess.check_output(
            "head -5 "+filename, shell=True).decode("utf-8").split("\n")
        for slicing_program in supported_slicers:
            if (slicing_program[0] in head[0]) or (slicing_program[0] in head[4]):
                try:
                    time, weight = slicing_program[1](filename)
                    piece.time = time
                    piece.weight = weight
                    piece.status = "101"  # FIXME Check if this state still holds
                    piece.save()
                    return True
                except:
                    break

        # If it reaches this point, something failed in finding the printing time
        # Set printing time to default for now..
        # TODO consider asking the user to input it manually or leaving the default

        piece.time = timedelta(hours=20)  # Default printing time
        piece.weight = 0.2  # Default weight
        piece.status = "101"  # In queue status
        piece.save()
        return True


def slicer_parser(print_file):
    """ Parser that reads the estimated printing time for gcodes that were
    sliced with Slic3r. """
    # Find last lines of the file
    lines = subprocess.check_output(
        "tail -350 "+filename, shell=True).decode("utf-8").split("\n")
    time_str = ""
    length_str = ""
    # Search for line that contains the printing time
    for line in lines:
        if "filament used" in line:
            length_str = line.split(" = ")[1]
        if "estimated printing time" in line:
            time_str = line.split(" = ")[1]
            break

    # Tries if it lasts more than an hour
    if "h" in time_str:
        hours = int(time_str.split("h ")[0])
        minutes = int(time_str.split("h ")[1].split("m ")[0])
        seconds = int(time_str.split("h ")[1].split("m ")[1].split("s")[0])
    else:
        hours = 0
        # Less than an hour but more than a minute
        if "m" in time_str:
            minutes = int(time_str.split("m ")[0])
            seconds = int(time_str.split("m ")[1].split("s")[0])
        # And less than a minute
        else:
            minutes = 0
            seconds = int(time_str.split("s")[0])

    dt = timedelta(hours=hours, minutes=minutes, seconds=seconds)

    # Get weigth
    length = int(length_str.split("mm")[0]) / 10  # in cm
    # PLA Density: 1.25 g/cm3
    radius = (piece.filament.diameter / 2) / 10  # in cm
    density = piece.filament.density  # in g/cm^3
    weight_g = radius**2 * pi * length * density  # in g
    weight_kg = weight_g / 1000  # in kg

    return dt, weight


def simplify_parser(print_file):
    """ Parser that reads the estimated printing time for gcodes that were
    sliced with Simplify3D. """

    lines = subprocess.check_output(
        "tail -5 "+filename, shell=True).decode("utf-8").split("\n")

    time_str = ""
    weight_str = ""

    for line in lines:
        if "Build time" in line:
            time_str = line.split(": ")[1]
        if "Plastic weight" in lines:
            weight_str = line.split(": ")[1]

    if "hours" in time_str:
        # TODO Continue this
        time_str = line.split(": ")[1]
        time_split = time_str.split(" hours ")
        hours = int(time_split[0])
        minutes = int(time_split[1].split(" minutes")[0])
        dt = timedelta(hours=hours, minutes=minutes)
    except:
        pass
    break


def cura_parser(print_file):
    """ Parser that reads the estimated printing time for gcodes that were
    sliced with Cura. """
