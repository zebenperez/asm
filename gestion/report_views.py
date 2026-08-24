from django.conf import settings
from django.db.models import CharField, DurationField, ExpressionWrapper, F, Sum
from django.contrib.postgres.lookups import Unaccent
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from asm.decorators import group_required
from asm.commons import get_float, get_int, get_or_none, get_param, get_session, set_session, show_exc, generate_qr, csv_export
from .models import *

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os, csv

CharField.register_lookup(Unaccent)


def init_session_date(request, key):
    set_session(request, key, datetime.now().strftime("%Y-%m-%d"))

'''
    REPORT
'''
def get_total_duration(item_list):
    total = 0
    for item in item_list:
        total += get_int(item.duration)
    return total

def get_report(request):
    cli = get_session(request, "s_rep_cli")
    cli_active = get_session(request, "s_rep_cli_active")
    #emp = get_session(request, "s_rep_emp")
    i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_rep_idate")), "%Y-%m-%d %H:%M")
    e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_rep_edate")), "%Y-%m-%d %H:%M")

    #kwargs = {"inactive": False}
    kwargs = {}
    if cli != "":
        kwargs["name__unaccent__icontains"] = cli
    if cli_active != "":
        kwargs["inactive"] = True if cli_active == "0" else False
    return Client.objects.filter(**kwargs)

    #kwargs = {"ini_date__range": (i_date, e_date)}
    #if cli != "":
    #    kwargs["client__name__unaccent__icontains"] = cli
    #if emp != "":
    #    kwargs["employee__name__unaccent__icontains"] = emp

    #return Assistance.objects.filter(**kwargs)

def get_assistances_report(request):
    cli = get_session(request, "s_rep_cli")
    cli_qr = get_session(request, "s_rep_cli_qr")
    emp = get_session(request, "s_rep_emp")
    i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_rep_idate")), "%Y-%m-%d %H:%M")
    e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_rep_edate")), "%Y-%m-%d %H:%M")

    kwargs = {"ini_date__range": (i_date, e_date)}
    if cli != "":
        kwargs["client__name__unaccent__icontains"] = cli
    if cli_qr != "":
        kwargs["client__qr_access"] = True if cli_qr == "True" else False
    if emp != "":
        kwargs["employee__name__unaccent__icontains"] = emp

    return Assistance.objects.filter(**kwargs)

# Versión anterior conservada como referencia. Hacía consultas dentro de los
# bucles de empleado, estado y cliente, por lo que el número de consultas
# crecía rápidamente con los resultados (patrón N+1).
#
# def get_employees_report(request):
#     emp = get_session(request, "s_rep_emp")
#     cli = get_or_none(Client, get_session(request, "s_rep_emp_cli"))
#     emp_type = get_session(request, "s_rep_emp_type")
#     emp_status = get_session(request, "s_rep_emp_status")
#     i_date = get_session(request, "s_rep_emp_idate")
#     e_date = get_session(request, "s_rep_emp_edate")
#     active = get_session(request, "s_rep_emp_active")
#     kwargs = {}
#     if emp != "":
#         kwargs["name__unaccent__icontains"] = emp
#     if emp_type != "":
#         kwargs["employee_type"] = emp_type
#     if active != "":
#         kwargs["inactive"] = True if active == "0" else False
#     res = []
#     emp_list = Employee.objects.filter(**kwargs)
#     status = TimetableStatus.objects.all()
#     for emp in emp_list:
#         res_dic = {"name": emp.name, "dni": emp.dni}
#         append = False
#         res_dic["status"] = []
#         def get_payers(client, timetable_status):
#             return ", ".join(emp.timetables.filter(date__range=(i_date, e_date), client=client, status=timetable_status, emp_type__payer__isnull=False).values_list("emp_type__payer__name", flat=True).distinct())
#         for s in status:
#             if emp_status == "" or emp_status == str(s.id):
#                 if cli is None:
#                     for item in emp.timetables.filter(date__range=(i_date, e_date)).order_by("client").distinct("client"):
#                         hours, minutes = emp.assigned_by_type(i_date, e_date, s, item.client)
#                         if item.client is not None and (hours > 0 or minutes > 0):
#                             res_dic["status"].append({"client": item.client.name, "payer": get_payers(item.client, s), "name": s.name, "hours": hours, "minutes": minutes})
#                             append = True
#                 else:
#                     hours, minutes = emp.assigned_by_type(i_date, e_date, s, cli)
#                     if hours > 0 or minutes > 0:
#                         res_dic["status"].append({"client": cli.name, "payer": get_payers(cli, s), "name": s.name, "hours": hours, "minutes": minutes})
#                         append = True
#         if append:
#             res_dic["total_hours"], res_dic["total_minutes"] = emp.assigned_by_type(i_date, e_date)
#             res.append(res_dic)
#     return res

def get_employees_report(request):
    """Genera el informe con una única consulta agregada de horarios."""
    emp = get_session(request, "s_rep_emp")
    cli_id = get_session(request, "s_rep_emp_cli")
    emp_type = get_session(request, "s_rep_emp_type")
    emp_status = get_session(request, "s_rep_emp_status")
    i_date = get_session(request, "s_rep_emp_idate")
    e_date = get_session(request, "s_rep_emp_edate")
    active = get_session(request, "s_rep_emp_active")

    filters = {
        "date__range": (i_date, e_date),
        "client__isnull": False,
        "employee__isnull": False,
    }
    if emp:
        filters["employee__name__unaccent__icontains"] = emp
    if cli_id:
        filters["client_id"] = cli_id
    if emp_type:
        filters["emp_type_id"] = emp_type
    if active:
        filters["employee__inactive"] = active == "0"

    duration = ExpressionWrapper(F("end") - F("ini"), output_field=DurationField())
    rows = (
        ClientTimetable.objects.filter(**filters)
        .values(
            "employee_id", "employee__name", "employee__dni", "client__name",
            "status_id", "status__name", "emp_type__name", "emp_type__payer__name",
        )
        .annotate(minutes=Sum(duration))
        .order_by("employee__name", "client__name", "status__name", "emp_type__payer__name")
    )

    employees = {}
    for row in rows:
        employee = employees.setdefault(
            row["employee_id"],
            {
                "name": row["employee__name"],
                "dni": row["employee__dni"],
                "status": [],
                "client_map": {},
                "total_minutes": 0,
            },
        )
        minutes = int(row["minutes"].total_seconds() // 60)
        employee["total_minutes"] += minutes
        if (
            row["status_id"]
            and (not emp_status or str(row["status_id"]) == emp_status)
            and minutes > 0
        ):
            status = {
                "client": row["client__name"],
                "emp_type": row["emp_type__name"] or "",
                "payer": row["emp_type__payer__name"] or "",
                "name": row["status__name"],
                "hours": minutes // 60,
                "minutes": minutes % 60,
            }
            employee["status"].append(status)
            client = employee["client_map"].setdefault(
                row["client__name"], {"name": row["client__name"], "status": []}
            )
            client["status"].append(status)

    result = []
    for employee in employees.values():
        total_minutes = employee.pop("total_minutes")
        if not employee["status"]:
            continue
        employee["clients"] = list(employee.pop("client_map").values())
        employee["total_hours"] = total_minutes // 60
        employee["total_minutes"] = total_minutes % 60
        result.append(employee)
    return result

@group_required("admins",)
def report(request):
    init_session_date(request, "s_rep_idate")
    init_session_date(request, "s_rep_edate")
    return render(request, "report/report.html", {"items": []})
    #return render(request, "report/report.html", {"items": get_report(request)})

@group_required("admins",)
def report_clients(request):
    init_session_date(request, "s_rep_idate")
    init_session_date(request, "s_rep_edate")
    return render(request, "report/report-clients.html", {"items": []})
    #return render(request, "report/report.html", {"items": get_report(request)})

@group_required("admins",)
def report_assistances(request):
    init_session_date(request, "s_rep_idate")
    init_session_date(request, "s_rep_edate")
    return render(request, "report/report-assistances.html", {"items": []})

@group_required("admins",)
def report_clients_list(request):
    item_list = get_report(request)
    return render(request, "report/report-clients-list.html", {"items": item_list, "duration": get_total_duration(item_list)})

@group_required("admins",)
def report_assistances_list(request):
    item_list = get_assistances_report(request)
    return render(request, "report/report-assistances-list.html", {"items": item_list, "duration": get_total_duration(item_list)})

@group_required("admins",)
def report_clients_search(request, clients=""):
    set_session(request, "s_rep_cli", get_param(request.GET, "s_rep_cli"))
    set_session(request, "s_rep_idate", get_param(request.GET, "s_rep_idate"))
    set_session(request, "s_rep_edate", get_param(request.GET, "s_rep_edate"))
    set_session(request, "s_rep_cli_active", get_param(request.GET, "s_rep_cli_active"))
    item_list = get_report(request)
    return render(request, "report/report-clients-list.html", {"items": item_list,})

@group_required("admins",)
def report_assistances_search(request, clients=""):
    set_session(request, "s_rep_emp", get_param(request.GET, "s_rep_emp"))
    set_session(request, "s_rep_cli", get_param(request.GET, "s_rep_cli"))
    set_session(request, "s_rep_cli_qr", get_param(request.GET, "s_rep_cli_qr"))
    set_session(request, "s_rep_idate", get_param(request.GET, "s_rep_idate"))
    set_session(request, "s_rep_edate", get_param(request.GET, "s_rep_edate"))
    item_list = get_assistances_report(request)
    return render(request, "report/report-assistances-list.html", {"items": item_list, "duration": get_total_duration(item_list),})
    #return render(request, "report/report-list.html", {"items": item_list, "duration": get_total_duration(item_list)})

@group_required("admins",)
def report_export(request):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    header = ['Cliente', 'Empleado', 'Fecha de inicio', 'Fecha de fin', 'Duración del servicio', 'Finalizada']
    values = []
    items = get_assistances_report(request)
    for item in items:
        ini_date = item.ini_date.astimezone(ZoneInfo("Atlantic/Canary"))
        idate = ini_date.strftime("%d-%m-%Y %H:%M")
        end_date = item.end_date.astimezone(ZoneInfo("Atlantic/Canary"))
        edate = end_date.strftime("%d-%m-%Y %H:%M")
        finish = "Si" if item.finish else "No"
        client = item.client.name if item.client != None else ""
        emp = item.employee.name if item.employee != None else ""
        row = [client, emp, idate, edate, item.duration, finish]
        values.append(row)
    return csv_export(header, values, "empleados")

@group_required("admins",)
def report_export_emp(request):
    header = ['Empleado', 'DNI', 'Tipo', 'Horas asignadas', 'Horas', 'Minutos']
    values = []
    items = get_employees_report(request)
    for item in items:
        emp = item["name"]
        dni = item["dni"]
        total = item["total_hours"]
        for s in item["status"]:
            row = [emp, dni, s["name"], f'{s["hours"]} horas y {s["minutes"]} minutos', s['hours'], s["minutes"]]
            #row = [emp, dni, s["name"], f'{s["hours"]} horas y {s["minutes"]} minutos', total]
            values.append(row)
    return csv_export(header, values, "empleados")

#@group_required("admins",)
#def report_search_emp(request):
#    try:
#        value = get_param(request.GET, "value")
#        items = Employee.objects.filter(name__unaccent__icontains=value) if value != "" else []
#        return render(request, "report/report-search-emp.html", {'items': items, 'value':value})
#    except Exception as e:
#        return render(request, "error_exception.html", {'exc':show_exc(e)})
#
#@group_required("admins",)
#def report_search_emp_cli(request):
#    try:
#        value = get_param(request.GET, "value")
#        items = Client.objects.filter(name__unaccent__icontains=value) if value != "" else []
#        return render(request, "report/report-search-emp-cli.html", {'items': items, 'value':value})
#    except Exception as e:
#        return render(request, "error_exception.html", {'exc':show_exc(e)})

@group_required("admins",)
def report_search_cli(request):
    try:
        value = get_param(request.GET, "value")
        items = Client.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "report/report-search-cli.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

@group_required("admins",)
def report_employees(request):
    init_session_date(request, "s_rep_emp_idate")
    init_session_date(request, "s_rep_emp_edate")
    set_session(request, "s_rep_emp", "")
    set_session(request, "s_rep_emp_type", "")
    context = {"items": [], 'emp_types': EmployeeType.objects.all(), 'status': TimetableStatus.objects.all()}
    return render(request, "report/report-employees.html", context)

@group_required("admins",)
def report_employees_list(request):
    item_list = get_employees_report(request)
    return render(request, "report/report-employees-list.html", {"items": item_list, 'status': TimetableStatus.objects.all()})

@group_required("admins",)
def report_employees_search(request, clients=""):
    set_session(request, "s_rep_emp", get_param(request.GET, "s_rep_emp"))
    set_session(request, "s_rep_emp_cli", get_param(request.GET, "s_rep_emp_cli"))
    set_session(request, "s_rep_emp_type", get_param(request.GET, "s_rep_emp_type"))
    set_session(request, "s_rep_emp_status", get_param(request.GET, "s_rep_emp_status"))
    set_session(request, "s_rep_emp_idate", get_param(request.GET, "s_rep_emp_idate"))
    set_session(request, "s_rep_emp_edate", get_param(request.GET, "s_rep_emp_edate"))
    set_session(request, "s_rep_emp_active", get_param(request.GET, "s_rep_emp_active"))
    item_list = get_employees_report(request)
    return render(request, "report/report-employees-list.html", {"items": item_list, 'status': TimetableStatus.objects.all()})
 

'''
    Empleados - Clientes - Estados
'''
def get_emp_cli_status_report(request):
    from django.db.models import Count

    emp = get_session(request, "s_rep_emp_cli_status_emp")
    cli = get_session(request, "s_rep_emp_cli_status_cli")
    status = get_session(request, "s_rep_emp_cli_status_status")
    i_date = get_session(request, "s_rep_emp_cli_status_idate")
    e_date = get_session(request, "s_rep_emp_cli_status_edate")

    kwargs = {}
    if emp != "":
        kwargs["employee__name__unaccent__icontains"] = emp
    if cli != "":
        kwargs["client__name__unaccent__icontains"] = cli
    if status != "":
        kwargs["status__id"] = status
    if i_date != "":
        kwargs["date__gte"] = i_date
    if e_date != "":
        kwargs["date__lte"] = e_date

    #item_list = ClientTimetable.objects.filter(**kwargs)
    item_list = (
        ClientTimetable.objects.filter(**kwargs)
        .values( "client__name", "employee__name", "status__name",)
        .annotate(total=Count("id"))
        .order_by("status__name", "employee__name", "client__name")
    )
    return item_list

@group_required("admins",)
def report_emp_cli_status(request):
    init_session_date(request, "s_rep_emp_cli_status_idate")
    init_session_date(request, "s_rep_emp_cli_status_edate")
    set_session(request, "s_rep_emp_cli_status_emp", "")
    set_session(request, "s_rep_emp_cli_status_cli", "")
    context = {"items": [], 'status': TimetableStatus.objects.all()}
    return render(request, "report/report-emp-cli-status/index.html", context)

@group_required("admins",)
def report_emp_cli_status_search(request, clients=""):
    set_session(request, "s_rep_emp_cli_status_emp", get_param(request.GET, "s_rep_emp_cli_status"))
    set_session(request, "s_rep_emp_cli_status_cli", get_param(request.GET, "s_rep_emp_cli_status_cli"))
    set_session(request, "s_rep_emp_cli_status_status", get_param(request.GET, "s_rep_emp_cli_status_status"))
    set_session(request, "s_rep_emp_cli_status_idate", get_param(request.GET, "s_rep_emp_cli_status_idate"))
    set_session(request, "s_rep_emp_cli_status_edate", get_param(request.GET, "s_rep_emp_cli_status_edate"))
    item_list = get_emp_cli_status_report(request)
    return render(request, "report/report-emp-cli-status/list.html", {"items": item_list, 'status': TimetableStatus.objects.all()})
 
@group_required("admins",)
def report_emp_cli_status_export(request):
    header = ['Empleado', 'Cliente', 'Estado']
    values = []
    items = get_emp_cli_status_report(request)
    for item in items:
        row = [item["employee__name"], item["client__name"], item["status__name"]]
        values.append(row)
    return csv_export(header, values, "empleados")
