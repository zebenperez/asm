from django.conf import settings
from django.db.models import CharField
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

def get_employees_report(request):
    emp = get_session(request, "s_rep_emp")
    cli = get_or_none(Client, get_session(request, "s_rep_emp_cli"))
    emp_type = get_session(request, "s_rep_emp_type")
    emp_status = get_session(request, "s_rep_emp_status")
    #i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_rep_idate")), "%Y-%m-%d %H:%M")
    #e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_rep_edate")), "%Y-%m-%d %H:%M")
    i_date = get_session(request, "s_rep_emp_idate")
    e_date = get_session(request, "s_rep_emp_edate")
    active = get_session(request, "s_rep_emp_active")

    #kwargs = {"ini_date__range": (i_date, e_date)}
    kwargs = {}
    if emp != "":
        kwargs["name__unaccent__icontains"] = emp
    if emp_type != "":
        kwargs["employee_type"] = emp_type
    if active != "":
        kwargs["inactive"] = True if active == "0" else False

    res = []
    emp_list = Employee.objects.filter(**kwargs)
    status = TimetableStatus.objects.all()
    for emp in emp_list:
        res_dic = {"name": emp.name, "dni": emp.dni}
        append = False
        res_dic["status"] = []
        for s in status:
            if (emp_status == "") or (emp_status == str(s.id)):
                hours, minutes = emp.assigned_by_type(i_date, e_date, s, cli)
                if hours > 0 or minutes > 0:
                    st_name = s.name if s != None else ""
                    cli_name = cli.name if cli != None else ""
                    res_dic["status"].append({"client": cli_name, "name": st_name, "hours": hours, "minutes": minutes})
                    append = True
        if append:
            h, m = emp.assigned_by_type(i_date, e_date)
            res_dic["total_hours"] = h
            res_dic["total_minutes"] = m
            res.append(res_dic)
    return res
    #return Assistance.objects.filter(**kwargs)

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

@group_required("admins",)
def report_search_emp(request):
    try:
        value = get_param(request.GET, "value")
        items = Employee.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "report/report-search-emp.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

@group_required("admins",)
def report_search_emp_cli(request):
    try:
        value = get_param(request.GET, "value")
        items = Client.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "report/report-search-emp-cli.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

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
@group_required("admins",)
def report_emp_cli_status(request):
    init_session_date(request, "s_rep_emp_cli_status_idate")
    init_session_date(request, "s_rep_emp_cli_status_edate")
    set_session(request, "s_rep_emp_cli_status", "")
    context = {"items": [], 'status': TimetableStatus.objects.all()}
    return render(request, "report/report-emp-cli-status/index.html", context)


