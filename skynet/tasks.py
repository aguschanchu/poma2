# Various tasks for PoMa 2

from .models import Piece, Order, Printer, Filament
from datetime import datetime, timedelta


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

        # TODO Implement this for other Slicing programs (Slimpify3D, Cura, etc)
        # TODO check if there is an easy an universal way of reading which slicing
        # program was used. before checking with evry single algorithm.
        slicing_programs = [slicer_parser]

        for program in slicing_programs:
            try:
                ept = program(filename)  # Estimated printing time
                piece.time = dt
                piece.status = '101'  # FIXME Check if this state still holds
                piece.save()
                return True
            except:
                continue

        # If none of the parsing algorithms worked, just set a default time
        # TODO Decide if this is the way to go, or to warn the user that the
        # printing time could not be found and therefore to slice again
        ept = timedelta(hours=25)
        piece.time = ept
        piece.status = '101'  # FIXME Check if this state still holds
        piece.save()
        return True


def slicer_parser(print_file):
    """ 
    Algorithm to find the estimated printing time of a gcode file if it was sliced
    using Slic3r.
    """
    # Find last lines of the file
    lines = subprocess.check_output(
        "tail -350 "+filename, shell=True).decode("utf-8").replace("; ", "").split("\n")
    time_str = ""
    # Search for line that contains the printing time
    for line in lines:
        if "estimated printing time (normal mode)" in line:
            time_str = line.split(" = ")[1]
            break
        # TODO Also check for the estimated weight of the piece

    # Parse the string to a timedelta format
    time_ref = datetime.strptime(time_str, "%Hh %Mm %Ss")
    basetime = datetime(1900, 1, 1)
    dt = time_ref - basetime  # Estimated printing time
    return dt
