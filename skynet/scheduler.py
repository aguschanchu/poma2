from __future__ import absolute_import, unicode_literals
from celery import shared_task, group
from ortools.sat.python import cp_model
import collections
import skynet.models as skynet_models
from django.conf import settings
import datetime
import pytz

'''
El Scheduler planifica las tareas de poma, y corre periodicamente. En lineas generales, realiza lo siguiente
1) Busca pedidos pendientes e impresoras libres
2) Calcula que pedidos pueden imprimirse en cada impresora
3) Calcula un escenario actual, en base a los pedidos que estan siendo procesados
4) Planifica las acciones futuras, utilizando modelos de ortools
5) En base al presente planificado, ejecuta las tareas de OctoprintTask
Actualmente, los constains que considera son:
1) Cumplir trabajos antes de deadline
2) Intervalos prohibidos
3) Posibilidad de imprimir en determinada impresora
'''


def print_piece_on_printer_check(piece, printer):
    # Size check - only for GM
    if piece.stl is not None:
        piece_size = sorted([piece.stl.orientation.size_x, piece.stl.orientation.size_y, piece.stl.orientation.size_z])
        printer_size = sorted(printer.printer_type.bed_shape)
        if not all([piece_size[i] < printer_size[i] for i in range(0, 3)]):
            return False
    # Print settings check
    if piece.print_settings is not None:
        if piece.print_settings != printer.printer_type:
            return False
    else:
        pass
    return True


def get_formatted_forbidden_bounds(horizon):
    '''
    Scheduler uses relative times, so, we need to translate it
    '''
    # We add timezone information
    tzinfo = pytz.timezone(settings.TIME_ZONE)
    now = datetime.datetime.now(tz=tzinfo)
    forbidden_zone = collections.namedtuple('zonet', 'start duration end')
    zones = [forbidden_zone(
        start=datetime.datetime.combine(datetime.datetime.today(), datetime.time(hour=x.start, tzinfo=now.tzinfo)),
        duration=datetime.timedelta(hours=x.duration),
        end=datetime.datetime.combine(datetime.datetime.today(),
                                      datetime.time(hour=x.start, tzinfo=now.tzinfo)) + datetime.timedelta(hours=x.duration))
        for x in settings.FORBIDDEN_ZONES]
    # We create a copy of each zone
    zones_in_horizon = []
    for zone in zones:
        zones_in_horizon += [forbidden_zone(start=zone.start+datetime.timedelta(days=j),
                                            duration=zone.duration,
                                            end=zone.end+datetime.timedelta(days=j))
                             for j in range(-2, horizon // (3600*24) +1)]

    fzones = []
    fzone_format = collections.namedtuple('fzone', 'start end')
    for zone in zones_in_horizon:
        # Are we currently on a forbidden zone?
        if now > zone.start and now < zone.end:
            fzones.append(fzone_format(start=60, end=round((zone.end-now).total_seconds())))
        elif now > zone.end:
            pass
        else:
            fzones.append(fzone_format(start=round((zone.start-now).total_seconds()), end=round((zone.end-now).total_seconds())))
    fzones = sorted(fzones, key=lambda x: x.start)
    # We create bounds according to AddLinearConstraintWithBounds needs
    bounds = [0, fzones[0].start]
    fzones_count = len(fzones)
    for i in range(0, fzones_count):
        if i == fzones_count - 1:
            bounds += [fzones[i].end, max(fzones[i].end, horizon)]
        else:
            bounds += [fzones[i].end, fzones[i+1].start]
    return bounds


@shared_task(queue='celery')
def poma_scheduler():
        # Pending pieces
        pending_pieces = []
        for p in skynet_models.Piece.objects.all():
            if p.quote_ready() and not p.cancelled:
                pending_pieces += [p for x in range(0, p.queued_pieces)]

        task_data_type = collections.namedtuple('task_data', 'id processing_time deadline processing_on')
        tasks_data = [task_data_type(p.id, int(p.get_build_time()), int(p.get_deadline_from_now()), None) for p in pending_pieces]

        # Machines
        available_machines = [p for p in skynet_models.Printer.objects.all() if p.printer_enabled]
        machines_count = len(available_machines)
        tasks_count = len(tasks_data)

        # Create the model.
        model = cp_model.CpModel()

        # Horizon definition
        horizon = sum([t.processing_time for t in tasks_data])

        # Forbidden zones definition
        bounds = get_formatted_forbidden_bounds(horizon)

        # Machines queue definition
        machines_queue = {}
        machines_corresp_to_db = {}
        for id, m in enumerate(available_machines):
            machines_queue[id] = []
            machines_corresp_to_db[id] = m.id

        # Pieces in progress
        for m in available_machines:
            if m.connection.active_task is not None:
                at = m.connection.active_task
                if not at.finished:
                    tasks_data.append(task_data_type('OT{}'.format(at.id), int(at.time_left), int(at.time_left), [x for x in machines_corresp_to_db.keys() if machines_corresp_to_db[x] == m.id][0]))
                    pass

        print(tasks_data)
        # Tasks creation
        task_type = collections.namedtuple('task', 'id data start end interval machine')
        task_optional_type = collections.namedtuple('task_optional', 'id start end interval machine flag')
        all_tasks = []
        task_queue = {}

        for task in tasks_data:
            start_var = model.NewIntVar(0, horizon, 'start_{id}'.format(id=task.id))
            end_var = model.NewIntVar(0, horizon, 'end_{id}'.format(id=task.id))
            interval = model.NewIntervalVar(start_var, task.processing_time, end_var, 'interval_{id}'.format(id=task.id))
            machine_var = model.NewIntVar(0, machines_count, 'machine_{id}'.format(id=task.id))
            all_tasks.append(task_type(id=task.id, data=task, start=start_var, end=end_var, interval=interval, machine=machine_var))
            # We create a copy of each interval, on each machine, as an OptionalIntervalVar, if we can print it on it
            task_queue[task.id] = []
            for m in machines_queue.keys():
                # Consider possible tasks and present tasks
                ## Possible tasks
                if task.processing_on is None:
                    # Printer compatibility check
                    if print_piece_on_printer_check(skynet_models.Piece.objects.get(id=task.id), skynet_models.Printer.objects.get(id=machines_corresp_to_db[m])):
                        start_var_o = model.NewIntVar(0, horizon, 'start_{id}_on_{machine}'.format(id=task.id, machine=m))
                        end_var_o = model.NewIntVar(0, horizon, 'end_{id}_on_{machine}'.format(id=task.id, machine=m))
                        flag = model.NewBoolVar('perform_{id}_on_{machine}'.format(id=task.id, machine=m))
                        task_queue[task.id].append(flag)
                        interval_o = model.NewOptionalIntervalVar(start_var_o, task.processing_time, end_var_o, flag,
                                                                  'interval_{id}_on_{machine}'.format(id=task.id, machine=m))
                        machines_queue[m].append(task_optional_type(id=task.id, start=start_var_o, end=end_var_o,
                                                                    interval=interval_o, machine=m, flag=flag))

                        ## We only propagate the constraint if the task is performed on the machine
                        model.Add(start_var == start_var_o).OnlyEnforceIf(flag)
                        model.Add(machine_var == m).OnlyEnforceIf(flag)
                ## Present tasks
                else:
                    if m == task.processing_on:
                        start_var_o = model.NewIntVar(0, horizon,
                                                      'start_{id}_on_{machine}'.format(id=task.id, machine=m))
                        end_var_o = model.NewIntVar(0, horizon, 'end_{id}_on_{machine}'.format(id=task.id, machine=m))
                        flag = model.NewBoolVar('perform_{id}_on_{machine}'.format(id=task.id, machine=m))
                        task_queue[task.id].append(flag)
                        interval_o = model.NewOptionalIntervalVar(start_var_o, task.processing_time, end_var_o, flag,
                                                                  'interval_{id}_on_{machine}'.format(id=task.id,
                                                                                                      machine=m))
                        machines_queue[m].append(task_optional_type(id=task.id, start=start_var_o, end=end_var_o,
                                                                    interval=interval_o, machine=m, flag=flag))

                        ## We only propagate the constraint if the task is performed on the machine
                        model.Add(start_var == start_var_o)
                        model.Add(machine_var == m)
                        model.Add(start_var_o == 0)
                        model.Add(flag == True)

        # Constrains

        ## Task_i is performed somewhere (and only on one machine)
        for t in task_queue.keys():
            model.AddBoolXOr(task_queue[t])

        ## Disjunctive constrains
        for m in range(machines_count):
            model.AddNoOverlap([t.interval for t in machines_queue[m]])

        ## Jobs should be ended by deadline
        for task_i in all_tasks:
            model.Add(task_i.end <= task_i.data.deadline)

        print(bounds)
        ## Forbidden zones constrains
        for task in all_tasks:
            model.AddLinearConstraintWithBounds([(task.start, 1)], bounds)

        # Makespan objective.
        obj_var = model.NewIntVar(0, horizon, 'makespan')
        model.AddMaxEquality(obj_var, [task.end for task in all_tasks])

        model.Minimize(obj_var)

        # Solve model.
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        print('Model validated: {}'.format(status == cp_model.OPTIMAL))
        if status == cp_model.OPTIMAL:
            for m in range(machines_count):
                # We sort task by start time
                order = lambda x: solver.Value(x.start)
                queue = [task for task in all_tasks if solver.Value(task.machine) == m]
                queue.sort(key=order)
                print("Machine {} schedule:".format(m))
                for t in queue:
                    print("Task {id}: start {start} ends {end} with {deadline} deadline".format(id=t.id,
                                                                                                start=round(float(solver.Value(t.start))/3600,2),
                                                                                                end=round(float(solver.Value(t.end))/3600,2),
                                                                                                deadline=round(float(t.data.deadline)/3600,2)))
        elif status == cp_model.MODEL_INVALID:
            print(model.Validate())
            print(model.ModelStats())

        else:
            print(status)




