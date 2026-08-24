from django.conf import settings
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Q
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
import locale
import calendar
import os, csv

CharField.register_lookup(Unaccent)
ACCESS_PATH="{}/gestion/assistances/client/".format(settings.MAIN_URL)

WEEK_DAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

def init_session_date(request, key):
    #if not key in request.session:
    set_session(request, key, datetime.now().strftime("%Y-%m-%d"))

def get_assistances(request):
    value = get_session(request, "s_name")
    i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_idate")), "%Y-%m-%d %H:%M")
    e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_edate")), "%Y-%m-%d %H:%M")

    kwargs = {"ini_date__gte": i_date, "ini_date__lte": e_date}
    if value != "":
        kwargs["employee__name__unaccent__icontains"] = value

    return Assistance.objects.filter(**kwargs).order_by("-ini_date")

@group_required("admins",)
def index(request):
    init_session_date(request, "s_idate")
    init_session_date(request, "s_edate")
    return render(request, "index.html", {"item_list": get_assistances(request)})

@group_required("admins",)
def assistances_list(request):
    return render(request, "assistances-list.html", {"item_list": get_assistances(request)})

@group_required("admins",)
def assistances_search(request):
    set_session(request, "s_name", get_param(request.GET, "s_name"))
    set_session(request, "s_idate", get_param(request.GET, "s_idate"))
    set_session(request, "s_edate", get_param(request.GET, "s_edate"))
    return render(request, "assistances-list.html", {"item_list": get_assistances(request)})

@group_required("admins",)
def assistances_form(request):
    obj = get_or_none(Assistance, get_param(request.GET, "obj_id"))
    context = {'obj': obj, 'client_list': Client.objects.all(), 'emp_list': Employee.objects.all()}
    return render(request, "assistances-form.html", context)

@group_required("admins",)
def assistances_form_save(request):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    obj = get_or_none(Assistance, get_param(request.GET, "obj_id"))
    if obj == None:
        obj = Assistance.objects.create()
    obj.client = get_or_none(Client, get_param(request.GET, "client"))
    obj.employee = get_or_none(Employee, get_param(request.GET, "employee"))
    ini_date = get_param(request.GET, "ini_date")
    end_date = get_param(request.GET, "end_date")
    ini_time = get_param(request.GET, "ini_time")
    end_time = get_param(request.GET, "end_time")
    finish = get_param(request.GET, "finish")
    idate = datetime.strptime("{} {}".format(ini_date, ini_time), "%Y-%m-%d %H:%M")
    edate = datetime.strptime("{} {}".format(end_date, end_time), "%Y-%m-%d %H:%M")
    idate = idate.replace(tzinfo=ZoneInfo("Atlantic/Canary"))
    edate = edate.replace(tzinfo=ZoneInfo("Atlantic/Canary"))
    idate = idate.astimezone(ZoneInfo("UTC"))
    edate = edate.astimezone(ZoneInfo("UTC"))

    obj.ini_date = idate
    obj.end_date = edate
    obj.finish = True if finish != "" else False
    obj.save()
    return render(request, "assistances-list.html", {"item_list": get_assistances(request)})

@group_required("admins",)
def assistances_remove(request):
    obj = get_or_none(Assistance, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "assistances-list.html", {"item_list": get_assistances(request)})

def assistances_client(request, client_id):
    return render(request, "assistances-client-error.html", {})

@group_required("admins",)
def assistances_search_emp(request):
    try:
        value = get_param(request.GET, "value")
        items = Employee.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "assistances-search-emp.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

@group_required("admins",)
def assistances_search_cli(request):
    try:
        value = get_param(request.GET, "value")
        items = Client.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "assistances-search-cli.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})


'''
    EMPLOYEES
'''
def get_employees(request):
    search_value = get_session(request, "s_emp_name")
    search_comp = get_session(request, "s_emp_comp")
    assigned = get_session(request, "s_emp_assign")
    adate_ini = get_session(request, "s_emp_adate_ini")
    adate_end = get_session(request, "s_emp_adate_end")

    #kwargs = {}
    #if search_value != "" or search_comp != "":
    #    if search_value != "":
    #        kwargs["name__unaccent__icontains"] = search_value
    #    if search_comp != "":
    #        kwargs["timetables__client__name__unaccent__icontains"] = search_comp
    #emp_list = Employee.objects.filter(**kwargs)
    filters = Q()
    if search_value:
        for word in search_value.split():
            filters &= Q(name__unaccent__icontains=word)
    if search_comp:
        for word in search_comp.split():
            filters &= Q(timetables__client__name__unaccent__icontains=word)
    emp_list = Employee.objects.filter(filters).distinct()

    if assigned != "":
        kwargs2 = {}
        if adate_ini != "":
            kwargs2["date__gte"] = adate_ini
        if adate_end != "":
            kwargs2["date__lte"] = adate_end
        emp_ids = list(ClientTimetable.objects.filter(**kwargs2).values_list('employee_id', flat=True).distinct())
        if assigned == "1":
            emp_list = emp_list.filter(id__in = emp_ids)
        else:
            emp_list = emp_list.exclude(id__in = emp_ids)

    return emp_list

@group_required("admins")
def employees_page_rows(request, page=1, rows=10):
    request.session["b_page"] = page
    request.session["b_rows"] = rows
    return redirect("employees")

@group_required("admins",)
def employees(request):
    init_session_date(request, "s_emp_idate")
    init_session_date(request, "s_emp_edate")
    if "b_page" not in request.session:
        request.session["b_page"] = 1
    if "b_rows" not in request.session:
        request.session["b_rows"] = 10
 
    items = get_employees(request)
    paginator = Paginator(items, get_int(request.session["b_rows"]))
    page_obj = paginator.get_page(request.session["b_page"])
    context = {
        'total_items': items.count(),
        'items': page_obj,
        'rows': request.session["b_rows"],
        'page_url': 'employees-page-rows',
        'active': 'employees'
    }

    return render(request, "employees/employees.html", context)

@group_required("admins",)
def employees_list(request):
    return render(request, "employees/employees-list.html", {"items": get_employees(request)})

@group_required("admins",)
def employees_search(request):
    set_session(request, "s_emp_name", get_param(request.GET, "s_emp_name"))
    set_session(request, "s_emp_comp", get_param(request.GET, "s_emp_comp"))
    #set_session(request, "s_emp_idate", get_param(request.GET, "s_emp_idate"))
    #set_session(request, "s_emp_edate", get_param(request.GET, "s_emp_edate"))
    set_session(request, "s_emp_assign", get_param(request.GET, "s_emp_assign"))
    set_session(request, "s_emp_adate_ini", get_param(request.GET, "s_emp_adate_ini"))
    set_session(request, "s_emp_adate_end", get_param(request.GET, "s_emp_adate_end"))
    return redirect("employees")
    #return render(request, "employees/employees-list.html", {"items": get_employees(request)})

@group_required("admins",)
def employees_new(request):
    return render(request, "employees/employees-new.html", {})

@group_required("admins",)
def employees_check_dni(request):
    dni = get_param(request.GET, "value")
    emp = Employee.objects.filter(dni=dni).first()
    return render(request, "employees/employees-check-dni.html", {'obj': emp, 'dni': dni})

@group_required("admins",)
def employees_form(request):
    obj_id = get_param(request.GET, "obj_id")
    dni = get_param(request.GET, "dni")
    obj = get_or_none(Employee, obj_id)
    if obj == None:
        obj = Employee.objects.create(dni=dni)
        obj.save_user_dni()
    context = {
        'obj': obj, 
        'zone_list': Zone.objects.all(), 
        'client_list': Client.objects.all(), 
        'self_type_list': SelfEmployedType.objects.all(),
        'type_list': EmployeeType.objects.all()
    }
    return render(request, "employees/employees-form.html", context)

@group_required("admins",)
def employees_remove(request):
    obj = get_or_none(Employee, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        if obj.user != None:
            obj.user.delete()
        obj.delete()
    return render(request, "employees/employees-list.html", {"items": get_employees(request)})

@group_required("admins",)
def employees_form_timetable(request):
    obj = get_or_none(Employee, get_param(request.GET, "obj_id"))
    #print(obj)
    if obj != None:
        client = get_or_none(Client, get_param(request.GET, "client"))
        days = request.GET.getlist("day")
        ini = get_param(request.GET, "ini")
        end = get_param(request.GET, "end")
        for day in days:
            ClientTimetable.objects.create(client=client, employee=obj, day=day, ini=ini, end=end)
    return render(request, "employees/employees-form-timetable.html", {'obj': obj, 'client_list': Client.objects.all()})

@group_required("admins",)
def employees_form_timetable_remove(request):
    obj = get_or_none(ClientTimetable, get_param(request.GET, "obj_id"))
    emp = None
    #print(obj)
    if obj != None:
        emp = obj.employee
        obj.delete()
    return render(request, "employees/employees-form-timetable.html", {'obj': emp, 'client_list': Client.objects.all(),})

@group_required("admins",)
def employees_save_email(request):
    try:
        obj = get_or_none(Employee, get_param(request.GET, "obj_id"))
        obj.email = get_param(request.GET, "value")
        obj.save()
        obj.save_user()
        return HttpResponse("Saved!")
    except Exception as e:
        return HttpResponse("Error: {}".format(e))

@group_required("admins",)
def employees_save_dni(request):
    try:
        obj = get_or_none(Employee, get_param(request.GET, "obj_id"))
        dni = get_param(request.GET, "value")
        if obj != None:
            emp = Employee.objects.filter(dni=dni).exclude(id=obj.id).first()
        else:
            emp = Employee.objects.filter(dni=dni).first()
        if emp != None:
            return HttpResponse(f"<div class='alert alert-danger'>Ese DNI ya esta asignado al usuario {emp.name}!</div>")

        if obj != None:
            obj.dni = dni
            obj.save()
            obj.save_user_dni()
        return HttpResponse("Saved!")
    except Exception as e:
        return HttpResponse("Error: {}".format(e))

@group_required("admins",)
def employees_save_cat(request):
    obj = get_or_none(Employee, get_param(request.GET, "obj_id"))
    emp_type = get_or_none(EmployeeType, get_param(request.GET, "type"))
    add = get_param(request.GET, "add")
    if obj != None:
        if add == "True":
            obj, created = EmployeeCategory.objects.get_or_create(employee=obj, employee_type=emp_type)
        else:
            EmployeeCategory.objects.filter(employee=obj, employee_type=emp_type).first().delete()
    return HttpResponse("Saved!")

@group_required("admins",)
def employees_export(request):
    header = ['Nombre', 'Teléfono', 'Email', 'PIN', 'DNI', 'Horas trabajadas', 'Minutos trabajados']
    values = []
    items = get_employees(request)
    for item in items:
        hours, minutes = item.worked_time(request.session["s_emp_idate"], request.session["s_emp_edate"])
        row = [item.name, item.phone, item.email, item.pin, item.dni, hours, minutes]
        values.append(row)
    return csv_export(header, values, "empleados")

@group_required("admins",)
def employees_import_csv(request):
    return render(request, "employees/import-csv.html", {})

@group_required("admins",)
def employees_import(request):
    f = request.FILES["file"]
    lines = f.read().decode('utf-8').splitlines()
    i = 0
    for line in lines:
        if i > 0:
            l = line.split(";")
            obj = Employee.objects.filter(dni=l[2]).first()
            if obj == None:
                obj = Employee.objects.create(dni=l[2])
            #print(l)
            obj.name = "{} {}".format(l[0], l[1])
            obj.phone = l[4] if len(l[4]) > 1 else l[5]
            obj.email = l[3]
            obj.dni = l[2]
            obj.save()
            #obj, created = Employee.objects.get_or_create(pin=dni, dni=dni, name=name, phone=phone, email=email)
            try:
                obj.save_user()
            except Exception as e:
                print(e)
        i += 1
    return redirect("employees")

@group_required("admins",)
def employees_copy_pin(request):
    for emp in Employee.objects.all():
        if emp.pin == "" and emp.dni != "":
            emp.pin = emp.dni
            emp.save()
    return render(request, "employees/copy-pin.html", {})

@group_required("admins",)
def employees_doc_add(request):
    try:
        obj = get_or_none(Employee, request.POST["obj_id"])
        if obj != None:
            file_list = request.FILES.getlist('file')
            for f in file_list:
                obj_doc = EmployeeDoc.objects.create(employee=obj)
                obj_doc.doc = f
                obj_doc.save()

        return render(request, "employees/employees-form-docs.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def employees_doc_remove(request):
    try:
        obj = get_or_none(EmployeeDoc, request.GET["obj_id"])
        if obj != None:
            emp = obj.employee
            obj.doc.delete(save=False)
            obj.delete()

        return render(request, "employees/employees-form-docs.html", {'obj': emp})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def employees_search_city(request):
    try:
        value = get_param(request.GET, "value")
        items = City.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "employees/employees-search-city.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

@group_required("admins",)
def employees_timetable(request, obj_id):
    return render(request, "employees/timetable/employees-timetable.html", {"obj": get_or_none(Employee, obj_id)})

@group_required("admins",)
def employees_timetable_load(request):
    date = get_param(request.GET, "date")
    employee = get_param(request.GET, "employee")
    try:
        timetable_list = ClientTimetable.objects.filter(employee__id=employee, date=date).exclude(client=None)
    except:
        timetable_list = []
    #print(timetable_list)
    return render(request, "employees/timetable/employees-timetable-box.html", {"timetable_list": timetable_list})

@group_required("admins",)
def employees_timetable_change_status(request):
    emp = get_param(request.GET, "obj_id")
    status_list = TimetableStatus.objects.all()
    return render(request, "employees/timetable/employees-timetable-change-status.html", {"emp": emp, "status_list": status_list})

@group_required("admins",)
def employees_timetable_set_status(request):
    obj = get_or_none(Employee, get_param(request.POST, "employee"))
    ini_date = get_param(request.POST, "ini_date")
    end_date = get_param(request.POST, "end_date")
    status = get_or_none(TimetableStatus, get_param(request.POST, "status"))
    if obj != None and status != None and ini_date != "" and end_date != "":
        timetables = ClientTimetable.objects.filter(employee=obj, date__range=(ini_date, end_date)).update(status=status)
    return redirect(reverse('employees-timetable', kwargs={'obj_id': obj.id}))

@group_required("admins",)
def employees_timetable_clients_add(request):
    emp = get_or_none(Employee, get_param(request.GET, "obj_id"))
    return render(request, "employees/timetable/employees-timetable-clients-add.html", {"obj": emp,})

@group_required("admins",)
def employees_timetable_clients_save(request):
    employee = get_or_none(Employee, get_param(request.GET, "obj_id"))
    client = get_or_none(Client, get_param(request.GET, "client"))
    if client != None and employee != None:
        ClientEmployee.objects.get_or_create(client=client, employee=employee)
    return render(request, "employees/timetable/employees-timetable-clients.html", {"obj": employee})

@group_required("admins",)
def employees_timetable_clients_remove(request):
    client = None
    obj = get_or_none(ClientEmployee, get_param(request.GET, "obj_id"))
    if obj != None:
        emp = obj.employee
        obj.delete()
    return render(request, "employees/timetable/employees-timetable-clients.html", {"obj": emp})

@group_required("admins",)
def employees_timetable_assign(request):
    obj = get_or_none(ClientEmployee, get_param(request.GET, "id"))
    date = get_param(request.GET, "date")

    d = datetime.strptime(date, "%Y-%m-%d")
    context = {
        'obj': obj,
        'date': date,
        'week_day': d.weekday(),
        'status_list': TimetableStatus.objects.all(),
        'emp_type_list': EmployeeType.objects.all(),
        'selected_emp_type': obj.employee.employee_type if obj and obj.employee else None,
        'new': True,
    }
    return render(request, "employees/timetable/employees-timetable-assign2.html", context)

@group_required("admins",)
def employees_timetable_assign_save2(request):
    timetable = get_or_none(ClientTimetable, get_param(request.GET, "timetable"))
    obj = get_or_none(ClientEmployee, get_param(request.GET, "obj_id"))
    date = get_param(request.GET, "date")
    ini = get_param(request.GET, "ini")
    end = get_param(request.GET, "end")
    ini_prev = get_param(request.GET, "ini_prev")
    end_prev = get_param(request.GET, "end_prev")
    emp_type = get_or_none(EmployeeType, get_param(request.GET, "emp_type"))
    repeat = get_param(request.GET, "repeat")
    monday = True if get_param(request.GET, "monday") == "true" else False
    tuesday = True if get_param(request.GET, "tuesday") == "true" else False
    wednesday = True if get_param(request.GET, "wednesday") == "true" else False
    thursday = True if get_param(request.GET, "thursday") == "true" else False
    friday = True if get_param(request.GET, "friday") == "true" else False
    saturday = True if get_param(request.GET, "saturday") == "true" else False
    sunday = True if get_param(request.GET, "sunday") == "true" else False
    cover = True if get_param(request.GET, "cover") == "true" else False
    status = get_or_none(TimetableStatus, get_param(request.GET, "status"))
    week_days = [monday, tuesday, wednesday, thursday, friday, saturday, sunday]

    client = timetable.client if timetable != None else obj.client
    employee = timetable.employee if timetable != None else obj.employee

    if repeat == "" and timetable != None:
        timetable.ini = ini
        timetable.end = end
        timetable.emp_type = emp_type
        timetable.status = status
        timetable.cover = cover
        timetable.save()
    else:
        d = datetime.strptime(date, "%Y-%m-%d")
        edate = get_edate(d, repeat)

        if repeat == "remove":
            ct = ClientTimetable.objects.filter(date__range=(d, edate), ini=ini, end=end, client=client, employee=employee)
            ct.delete()
        else:
            current = d
            current_month = d.month
            repeat_list = [0,0,0,0,0,0,0]
            while current <= edate:
                if repeat == "month" or repeat =="year" or repeat == "":
                    #print(f'Fecha {current} - {week_days[current.weekday()]}')
                    if week_days[current.weekday()]:
                        goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev, cover, emp_type, True)
                elif repeat == "year_month_once" or repeat == "year_month_twice":
                    iday = current.weekday()
                    if current.month != current_month:
                        current_month = current.month
                        repeat_list = [0,0,0,0,0,0,0]
                    if week_days[iday]:
                        repeat_list[iday] += 1
                        if ((repeat == "year_month_once" and repeat_list[iday] == 1) 
                            or (repeat == "year_month_twice" and (repeat_list[iday] == 1 or repeat_list[iday] == 3))):
                            goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev, cover, emp_type, True)
                current += timedelta(days=1)

    return render(request, "employees/timetable/employees-timetable-reload.html", {})

@group_required("admins",)
def employees_timetable_assign_edit(request):
    timetable = get_or_none(ClientTimetable, get_param(request.GET, "id"))
    obj = ClientEmployee.objects.filter(client=timetable.client, employee=timetable.employee).first()
    date = timetable.date.strftime("%Y-%m-%d")

    context = {
        "obj": obj, 
        "timetable": timetable, 
        "date": date, 
        #"week_day": WEEK_DAYS[timetable.date.weekday()], 
        "week_day": timetable.date.weekday(), 
        'status_list': TimetableStatus.objects.all(),
        'emp_type_list': EmployeeType.objects.all(),
        'selected_emp_type_id': timetable.emp_type_id or timetable.employee.employee_type_id,
    }
    return render(request, "employees/timetable/employees-timetable-assign2.html", context)


'''
    CLIENTS
'''
def get_clients(request, limit=50):
    name = get_session(request, "s_cli_name").lstrip()
    cif = get_session(request, "s_cli_cif").lstrip()
    ctype = get_session(request, "s_cli_type")
    city = get_session(request, "s_cli_city")
    active = get_session(request, "s_cli_active")
    date_ini = get_session(request, "s_cli_date_ini")
    date_end = get_session(request, "s_cli_date_end")
    itype = get_session(request, "s_cli_itype")
    assigned = get_session(request, "s_cli_assigned")
    adate_ini = get_session(request, "s_cli_adate_ini")
    adate_end = get_session(request, "s_cli_adate_end")

    kwargs = {}
    name_query = Q()
    if name != "":
        #kwargs["name__unaccent__icontains"] = name 
        for n in name.split():
            name_query &= Q(name__unaccent__icontains = n)
    if cif != "":
        kwargs["code__icontains"] = cif
    if city != "":
        kwargs["city__id"] = city
        #kwargs["city__icontains"] = city
    if active != "":
        kwargs["inactive"] = True if active == "0" else False
    if ctype != "":
        client_ids = [item.client.id for item in ClientTypeAmount.objects.filter(client_type__id=ctype)]
        kwargs["id__in"] = client_ids
    if itype != "" or date_ini != "" or date_end != "":
        kwargs2 = {}
        if itype != "":
            kwargs2["itype__id"] = itype
        if date_ini != "":
            kwargs2["date__gte"] = date_ini
        if date_end != "":
            kwargs2["date__lte"] = date_end
        #client_ids = [item.client.id for item in ClientInactive.objects.filter(**kwargs2)]
        client_ids = list(ClientInactive.objects.filter(**kwargs2).values_list('client_id', flat=True).distinct())
        kwargs["id__in"] = client_ids

    client_list = Client.objects.filter(name_query, **kwargs)

    if assigned != "":
        kwargs2 = {}
        if adate_ini != "":
            kwargs2["date__gte"] = adate_ini
        if adate_end != "":
            kwargs2["date__lte"] = adate_end
        client_ids = list(ClientTimetable.objects.filter(**kwargs2).values_list('client_id', flat=True).distinct())
        if assigned == "1":
            client_list = client_list.filter(id__in = client_ids)
        else:
            client_list = client_list.exclude(id__in = client_ids)

    return client_list.order_by("-id")[:limit] if limit > 0 else client_list.order_by("-id")
    #filters_to_search = ["name__unaccent__icontains",]
    #full_query = Q()
    #if search_value != "":
    #    for myfilter in filters_to_search:
    #        full_query |= Q(**{myfilter: search_value})
    #print(full_query)
    #return Client.objects.filter(full_query).order_by("-id")[:50]

@group_required("admins",)
def clients(request):
    type_list = ClientType.objects.all()
    itype_list = ClientInactiveType.objects.all()
    city_list = City.objects.all()
    context = {"items": get_clients(request), 'type_list': type_list, 'city_list': city_list, 'itype_list': itype_list}
    return render(request, "clients/clients.html", context)

@group_required("admins",)
def clients_list(request):
    return render(request, "clients/clients-list.html", {"items": get_clients(request)})

@group_required("admins",)
def clients_search(request):
    set_session(request, "s_cli_name", get_param(request.GET, "s_cli_name"))
    set_session(request, "s_cli_cif", get_param(request.GET, "s_cli_cif"))
    set_session(request, "s_cli_type", get_param(request.GET, "s_cli_type"))
    set_session(request, "s_cli_city", get_param(request.GET, "s_cli_city"))
    set_session(request, "s_cli_active", get_param(request.GET, "s_cli_active"))
    set_session(request, "s_cli_date_ini", get_param(request.GET, "s_cli_date_ini"))
    set_session(request, "s_cli_date_end", get_param(request.GET, "s_cli_date_end"))
    set_session(request, "s_cli_itype", get_param(request.GET, "s_cli_itype"))
    set_session(request, "s_cli_assigned", get_param(request.GET, "s_cli_assignes"))
    set_session(request, "s_cli_adate_ini", get_param(request.GET, "s_cli_adate_ini"))
    set_session(request, "s_cli_adate_end", get_param(request.GET, "s_cli_adate_end"))
    return render(request, "clients/clients-list.html", {"items": get_clients(request)})

@group_required("admins",)
def clients_form(request):
    #obj = get_or_none(Client, get_param(request.GET, "obj_id"))
    #new = False
    #if obj == None:
    #    obj = Client.objects.create()
    #    url = "{}{}".format(ACCESS_PATH, obj.id)
    #    path = os.path.join(settings.BASE_DIR, "static", "images", "logo-asistencia-canaria.jpg")
    #    img_data = ContentFile(generate_qr(url, path))
    #    obj.qr.save('qr_{}.png'.format(obj.id), img_data, save=True)
    #    new = True
    #context = {'obj': obj, 'new': new, 'emp_list': Employee.objects.all(), 'type_list': ClientType.objects.all()}
    context = {'emp_list': Employee.objects.all(), 'type_list': ClientType.objects.all()}
    return render(request, "clients/clients-form.html", context)

@group_required("admins",)
def clients_form_save(request):
    name = get_param(request.GET, "name")
    code = get_param(request.GET, "code")

    obj = Client.objects.filter(code=code).first()
    if obj != None:
        return render(request, "clients/clients-err.html", {'obj': obj})

    obj = Client.objects.create(name=name, code=code)
    url = "{}{}".format(ACCESS_PATH, obj.id)
    path = os.path.join(settings.BASE_DIR, "static", "images", "logo-asistencia-canaria.jpg")
    img_data = ContentFile(generate_qr(url, path))
    obj.qr.save('qr_{}.png'.format(obj.id), img_data, save=True)

    return redirect(reverse('clients-details', kwargs={'obj_id': obj.id}))
    #context = {'obj': obj, 'emp_list': Employee.objects.all(), 'type_list': ClientType.objects.all(), 'today': datetime.today()}
    #return render(request, "clients/clients-details.html", context)

@group_required("admins",)
def clients_details(request, obj_id):
    obj = get_or_none(Client, obj_id)
    context = {
        'obj': obj, 
        'emp_list': Employee.objects.all(), 
        'type_list': ClientType.objects.all(), 
        'itype_list': ClientInactiveType.objects.all(), 
        'stype_list': ClientStoppedType.objects.all(), 
        'timetable_status_list': TimetableStatus.objects.filter(calc=False), 
        'grade_list': ClientGrade.objects.all(), 
        'today': datetime.today()
    }
    print(context)
    return render(request, "clients/clients-details.html", context)

@group_required("admins",)
def clients_form_timetable(request):
    obj = get_or_none(Client, get_param(request.GET, "obj_id"))
    #print(obj)
    if obj != None:
        emp = get_or_none(Employee, get_param(request.GET, "employee"))
        days = request.GET.getlist("day")
        ini = get_param(request.GET, "ini")
        end = get_param(request.GET, "end")
        for day in days:
            ClientTimetable.objects.create(client=obj, employee=emp, day=day, ini=ini, end=end)
    return render(request, "clients/clients-form-timetable.html", {'obj': obj, 'emp_list': Employee.objects.all()})

@group_required("admins",)
def clients_remove(request):
    obj = get_or_none(Client, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.qr.delete(save=True)
        obj.delete()
    return render(request, "clients/clients-list.html", {"items": get_clients(request)})

@group_required("admins",)
def clients_form_timetable_remove(request):
    obj = get_or_none(ClientTimetable, get_param(request.GET, "obj_id"))
    client = None
    #print(obj)
    if obj != None:
        client = obj.client
        obj.delete()
    return render(request, "clients/clients-form-timetable.html", {'obj': client, 'emp_list': Employee.objects.all(),})

@group_required("admins",)
def clients_print_all_qr(request):
    return render(request, "clients/clients-print-all-qr.html", {"item_list": Client.objects.filter(inactive=False)})

@group_required("admins",)
def clients_print_qr(request, obj_id):
    return render(request, "clients/clients-print-qr.html", {"obj": get_or_none(Client, obj_id)})

@group_required("admins",)
def clients_assistances(request, obj_id):
    return render(request, "clients/clients-assistances.html", {"obj": get_or_none(Client, obj_id)})

@group_required("admins")
def clients_import_csv(request):
    return render(request, "clients/import-csv.html", {})

@group_required("admins")
def clients_import(request):
    try:
        f = request.FILES["file"]

        lines = f.read().decode('utf-8').splitlines()
        i = 0
        for line in lines:
            if i > 0:
                l = line.split(";")
                #print(l)
                obj = Client.objects.filter(code=l[1]).first()
                if obj == None:
                    obj = Client.objects.create(code=l[1])
                obj.name = l[0]
                obj.address = l[2]
                obj.phone = l[3]
                obj.email = l[4]
                obj.amount = get_float(l[5])
                obj.city = l[6]
                obj.save()
            i += 1
        return redirect("clients")
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def clients_export_csv(request):
    header = ['Nombre', 'NIF', 'Dirección', 'Teléfono', 'Correo electrónico', 'Cantidad', 'Municipio']
    values = []
    items = get_clients(request, -1)
    for item in items:
        row = [item.name, item.code, item.address, item.phone, item.email, item.amount, item.city]
        values.append(row)
    return csv_export(header, values, "empleados")

@group_required("admins",)
def clients_timetable(request, obj_id):
    return render(request, "clients/timetable/clients-timetable.html", {"obj": get_or_none(Client, obj_id)})

@group_required("admins",)
def clients_timetable_employees_add(request):
    client = get_or_none(Client, get_param(request.GET, "obj_id"))
    context = {"obj": client, "emp_list": Employee.objects.all()}
    return render(request, "clients/timetable/clients-timetable-employees-add.html", context)

@group_required("admins",)
def clients_timetable_employees_save(request):
    client = get_or_none(Client, get_param(request.GET, "obj_id"))
    emp_list = request.GET.getlist("values[]")
    for emp in emp_list:
        employee = get_or_none(Employee, emp)
        if employee != None:
            ClientEmployee.objects.get_or_create(client=client, employee=employee)
    return render(request, "clients/timetable/clients-timetable-employees.html", {"obj": client})

@group_required("admins",)
def clients_timetable_employees_remove(request):
    client = None
    obj = get_or_none(ClientEmployee, get_param(request.GET, "obj_id"))
    if obj != None:
        client = obj.client
        obj.delete()
    return render(request, "clients/timetable/clients-timetable-employees.html", {"obj": client})

@group_required("admins",)
def clients_timetable_load(request):
    date = get_param(request.GET, "date")
    client = get_param(request.GET, "client")
    try:
        timetable_list = ClientTimetable.objects.filter(client__id=client, date=date)
    except:
        timetable_list = []
    return render(request, "clients/timetable/clients-timetable-box.html", {"timetable_list": timetable_list})

@group_required("admins",)
def clients_timetable_assign(request):
    obj = get_or_none(ClientEmployee, get_param(request.GET, "id"))
    date = get_param(request.GET, "date")

    d = datetime.strptime(date, "%Y-%m-%d")
    #context = {'obj': obj, 'date': date, 'week_day':WEEK_DAYS[d.weekday()], 'status_list': TimetableStatus.objects.all(), 'new': True}
    context = {'obj': obj, 'date': date, 'week_day': d.weekday(), 'status_list': TimetableStatus.objects.all(), 'new': True}
    return render(request, "clients/timetable/clients-timetable-assign2.html", context)

def goc_client_timetable(date, ini, end, client, emp, st, ini_prev, end_prev, cover=False, emp_type=None, update_emp_type=False):
    ct = ClientTimetable.objects.filter(date=date, ini=ini_prev, end=end_prev, client=client, employee=emp).first()
    if ct == None:
        return ClientTimetable.objects.create(date=date, ini=ini, end=end, client=client, employee=emp, emp_type=emp_type, status=st, cover=cover)
    ct.ini = ini
    ct.end = end
    if update_emp_type:
        ct.emp_type = emp_type
    ct.status = st
    ct.cover = cover
    ct.save()
    return ct
    #return ClientTimetable.objects.get_or_create(date=date, ini=ini, end=end, client=client, employee=emp, status=st)

@group_required("admins",)
def clients_timetable_assign_save(request):
    timetable = get_or_none(ClientTimetable, get_param(request.GET, "timetable"))
    obj = get_or_none(ClientEmployee, get_param(request.GET, "obj_id"))
    date = get_param(request.GET, "date")
    ini = get_param(request.GET, "ini")
    end = get_param(request.GET, "end")
    ini_prev = get_param(request.GET, "ini_prev")
    end_prev = get_param(request.GET, "end_prev")
    repeat = get_param(request.GET, "repeat")
    status = get_or_none(TimetableStatus, get_param(request.GET, "status"))

    client = timetable.client if timetable != None else obj.client
    employee = timetable.employee if timetable != None else obj.employee

    if repeat == "":
        if timetable != None:
            timetable.ini = ini
            timetable.end = end
            timetable.status = status
            timetable.save()
        else:
            timetable = ClientTimetable.objects.create(date=date, ini=ini, end=end, client=client, employee=employee, status=status)
    else:
    #if repeat != "":
        d = datetime.strptime(date, "%Y-%m-%d")
        keys = ["year", "week_year", "remove", "one_day_month", "two_days_month"]
        edate = d + relativedelta(month=12, day=31) if repeat in keys else d + relativedelta(day=31)
        if repeat == "remove":
            ct = ClientTimetable.objects.filter(date__range=(d, edate), ini=ini, end=end, client=client, employee=employee)
            ct.delete()
        else:
            current = d
            current_month = d.month
            i = 0
            while current <= edate:
                if repeat == "week" or repeat == "week_year":
                    if current.weekday() == d.weekday():
                        goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev)
                elif repeat == "month" or repeat == "year":
                    if current.weekday() not in [5, 6]:
                        goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev)
                elif repeat == "one_day_month" or repeat == "two_days_month":
                    if current.month != current_month:
                        current_month = current.month
                        i = 0
                    if current.weekday() == d.weekday():
                        i += 1
                        if ((repeat == "one_day_month" and i == 1) or (repeat == "two_days_month" and (i == 1 or i == 3))):
                            goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev)

                current += timedelta(days=1)

    return render(request, "clients/timetable/clients-timetable-reload.html", {})
    #return render(request, "clients/timetable/clients-timetable-box.html", {"timetable_list": timetable.get_in_same_day()})

def get_edate(d, repeat):
    if repeat == "month":
        return d + relativedelta(day=31)
    elif repeat == "year" or repeat == "year_month_once" or repeat == "year_month_twice" or repeat == "remove":
        return d + relativedelta(month=12, day=31)
    return d + relativedelta(days=6)

@group_required("admins",)
def clients_timetable_assign_save2(request):
    timetable = get_or_none(ClientTimetable, get_param(request.GET, "timetable"))
    obj = get_or_none(ClientEmployee, get_param(request.GET, "obj_id"))
    date = get_param(request.GET, "date")
    ini = get_param(request.GET, "ini")
    end = get_param(request.GET, "end")
    ini_prev = get_param(request.GET, "ini_prev")
    end_prev = get_param(request.GET, "end_prev")
    repeat = get_param(request.GET, "repeat")
    monday = True if get_param(request.GET, "monday") == "true" else False
    tuesday = True if get_param(request.GET, "tuesday") == "true" else False
    wednesday = True if get_param(request.GET, "wednesday") == "true" else False
    thursday = True if get_param(request.GET, "thursday") == "true" else False
    friday = True if get_param(request.GET, "friday") == "true" else False
    saturday = True if get_param(request.GET, "saturday") == "true" else False
    sunday = True if get_param(request.GET, "sunday") == "true" else False
    cover = True if get_param(request.GET, "cover") == "true" else False
    status = get_or_none(TimetableStatus, get_param(request.GET, "status"))
    week_days = [monday, tuesday, wednesday, thursday, friday, saturday, sunday]

    client = timetable.client if timetable != None else obj.client
    employee = timetable.employee if timetable != None else obj.employee

    if repeat == "" and timetable != None:
            timetable.ini = ini
            timetable.end = end
            timetable.status = status
            timetable.cover = cover
            timetable.save()
    else:
        d = datetime.strptime(date, "%Y-%m-%d")
        edate = get_edate(d, repeat)

        if repeat == "remove":
            ct = ClientTimetable.objects.filter(date__range=(d, edate), ini=ini, end=end, client=client, employee=employee)
            ct.delete()
        else:
            current = d
            current_month = d.month
            repeat_list = [0,0,0,0,0,0,0]
            while current <= edate:
                if repeat == "month" or repeat =="year" or repeat == "":
                    #print(f'Fecha {current} - {week_days[current.weekday()]}')
                    if week_days[current.weekday()]:
                        goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev, cover)
                elif repeat == "year_month_once" or repeat == "year_month_twice":
                    iday = current.weekday()
                    if current.month != current_month:
                        current_month = current.month
                        repeat_list = [0,0,0,0,0,0,0]
                    if week_days[iday]:
                        repeat_list[iday] += 1
                        if ((repeat == "year_month_once" and repeat_list[iday] == 1) 
                            or (repeat == "year_month_twice" and (repeat_list[iday] == 1 or repeat_list[iday] == 3))):
                            goc_client_timetable(current, ini, end, client, employee, status, ini_prev, end_prev, cover)
                current += timedelta(days=1)

    return render(request, "clients/timetable/clients-timetable-reload.html", {})
 
@group_required("admins",)
def clients_timetable_assign_edit(request):
    timetable = get_or_none(ClientTimetable, get_param(request.GET, "id"))
    obj = ClientEmployee.objects.filter(client=timetable.client, employee=timetable.employee).first()
    date = timetable.date.strftime("%Y-%m-%d")

    context = {
        "obj": obj, 
        "timetable": timetable, 
        "date": date, 
        #"week_day": WEEK_DAYS[timetable.date.weekday()], 
        "week_day": timetable.date.weekday(), 
        'status_list': TimetableStatus.objects.all()
    }
    return render(request, "clients/timetable/clients-timetable-assign2.html", context)

@group_required("admins",)
def clients_timetable_assign_remove(request):
    timetable = get_or_none(ClientTimetable, get_param(request.GET, "id"))
    timetable_list = timetable.get_in_same_day().exclude(id=timetable.id)
    #print(timetable_list)
    timetable.delete()
    return render(request, "clients/timetable/clients-timetable-box.html", {"timetable_list": timetable_list})

@group_required("admins",)
def clients_doc_add(request):
    try:
        obj = get_or_none(Client, request.POST["obj_id"])
        if obj != None:
            file_list = request.FILES.getlist('file')
            for f in file_list:
                obj_doc = ClientDoc.objects.create(client=obj)
                obj_doc.doc = f
                obj_doc.save()

        return render(request, "clients/clients-details-docs.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_doc_remove(request):
    try:
        obj = get_or_none(ClientDoc, request.GET["obj_id"])
        if obj != None:
            client = obj.client
            obj.doc.delete(save=False)
            obj.delete()

        return render(request, "clients/clients-details-docs.html", {'obj': client})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_type_add(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        client_type = get_or_none(ClientType, get_param(request.GET, "type"))
        amount = get_param(request.GET, "amount").replace(",", ".")
        
        if obj != None:
            cta, created = ClientTypeAmount.objects.get_or_create(client=obj, client_type=client_type)
            cta.amount = get_float(amount)
            cta.save()

        return render(request, "clients/clients-details-types.html", {'obj': obj, 'type_list': ClientType.objects.all()})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_type_remove(request):
    try:
        obj = get_or_none(ClientTypeAmount, request.GET["obj_id"])
        if obj != None:
            client = obj.client
            obj.delete()

        return render(request, "clients/clients-details-types.html", {'obj': client, 'type_list': ClientType.objects.all()})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_inactive_confirm(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        emp_ids = obj.timetables.filter(date__gte=datetime.today()).values_list('employee', flat=True).distinct()
        emp_list = Employee.objects.filter(id__in = emp_ids)
        context = {'obj': obj, 'emp_list': emp_list, 'today': datetime.today(), 'itype_list': ClientInactiveType.objects.all()}
        return render(request, "clients/clients-details-inactive-confirm.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_inactive_set(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        #obj.inactive = True if not obj.inactive else False
        obj.inactive = False
        obj.save()
        context = {'obj': obj, 'today': datetime.today(), 'itype_list': ClientInactiveType.objects.all()}
        return render(request, "clients/clients-details-inactive.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_inactive_add(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        itype = get_or_none(ClientInactiveType, get_param(request.GET, "itype"))
        date = get_param(request.GET, "date")
        obs = get_param(request.GET, "obs")
        
        if obj != None:
            obj.inactive = True
            obj.save()
            ci = ClientInactive.objects.create(client=obj, date=date, obs=obs, itype=itype)
            obj.remove_timetable_from_date(date)

        return render(request, "clients/clients-details-inactive.html", {'obj': obj, 'today': datetime.today(),})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_inactive_remove(request):
    try:
        obj = get_or_none(ClientInactive, request.GET["obj_id"])
        if obj != None:
            client = obj.client
            obj.delete()

        return render(request, "clients/clients-details-inactive.html", {'obj': client, 'today': datetime.today(),})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def get_stopped_context(obj):
    return {
        'obj': obj, 
        'today': datetime.today(),
        'stype_list': ClientStoppedType.objects.all(), 
        'timetable_status_list': TimetableStatus.objects.filter(calc=False)
    }

@group_required("admins",)
def clients_stopped_confirm(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        emp_ids = obj.timetables.filter(date__gte=datetime.today()).values_list('employee', flat=True).distinct()
        context = {
            'obj': obj, 
            'today': datetime.today(), 
            'emp_list': Employee.objects.filter(id__in = emp_ids),
            'ts_list': TimetableStatus.objects.filter(),
            'stype_list': ClientStoppedType.objects.all(),
            'timetable_status_list': TimetableStatus.objects.filter(calc=False)
        }
        return render(request, "clients/clients-details-stopped-confirm.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_stopped_set(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        ts = get_or_none(TimetableStatus, get_param(request.GET, "ts"))
        if not obj.stopped:
            obj.stopped = True 
            obj.save()
        else:
            obj.stopped = False
            obj.save()
            obj.set_timetable_status_from_date(datetime.today(), ts)
        return render(request, "clients/clients-details-stopped.html", get_stopped_context(obj))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_stopped_add(request):
    try:
        obj = get_or_none(Client, get_param(request.GET, "obj_id"))
        date = get_param(request.GET, "date")
        stype = get_or_none(ClientStoppedType, get_param(request.GET, "stype"))
        ts = get_or_none(TimetableStatus, get_param(request.GET, "timetable_status"))
        obs = get_param(request.GET, "obs")
        
        if obj != None:
            obj.stopped = True 
            obj.save()
            cs = ClientStopped.objects.create(client=obj, date=date, obs=obs, stype=stype)
            obj.set_timetable_status_from_date(date, ts)

        return render(request, "clients/clients-details-stopped.html", get_stopped_context(obj))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_stopped_remove(request):
    try:
        obj = get_or_none(ClientStopped, request.GET["obj_id"])
        if obj != None:
            client = obj.client
            obj.delete()

        return render(request, "clients/clients-details-stopped.html", get_stopped_context(client))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def clients_search_city(request):
    try:
        value = get_param(request.GET, "value")
        items = City.objects.filter(name__unaccent__icontains=value) if value != "" else []
        return render(request, "clients/clients-search-city.html", {'items': items, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})


#'''
#    REPORT
#'''
#def get_total_duration(item_list):
#    total = 0
#    for item in item_list:
#        total += get_int(item.duration)
#    return total
#
#def get_report(request):
#    cli = get_session(request, "s_rep_cli")
#    cli_active = get_session(request, "s_rep_cli_active")
#    #emp = get_session(request, "s_rep_emp")
#    i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_rep_idate")), "%Y-%m-%d %H:%M")
#    e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_rep_edate")), "%Y-%m-%d %H:%M")
#
#    #kwargs = {"inactive": False}
#    kwargs = {}
#    if cli != "":
#        kwargs["name__unaccent__icontains"] = cli
#    if cli_active != "":
#        kwargs["inactive"] = True if cli_active == "0" else False
#    return Client.objects.filter(**kwargs)
#
#    #kwargs = {"ini_date__range": (i_date, e_date)}
#    #if cli != "":
#    #    kwargs["client__name__unaccent__icontains"] = cli
#    #if emp != "":
#    #    kwargs["employee__name__unaccent__icontains"] = emp
#
#    #return Assistance.objects.filter(**kwargs)
#
#def get_assistances_report(request):
#    cli = get_session(request, "s_rep_cli")
#    cli_qr = get_session(request, "s_rep_cli_qr")
#    emp = get_session(request, "s_rep_emp")
#    i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_rep_idate")), "%Y-%m-%d %H:%M")
#    e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_rep_edate")), "%Y-%m-%d %H:%M")
#
#    kwargs = {"ini_date__range": (i_date, e_date)}
#    if cli != "":
#        kwargs["client__name__unaccent__icontains"] = cli
#    if cli_qr != "":
#        kwargs["client__qr_access"] = True if cli_qr == "True" else False
#    if emp != "":
#        kwargs["employee__name__unaccent__icontains"] = emp
#
#    return Assistance.objects.filter(**kwargs)
#
#def get_employees_report(request):
#    emp = get_session(request, "s_rep_emp")
#    cli = get_or_none(Client, get_session(request, "s_rep_emp_cli"))
#    emp_type = get_session(request, "s_rep_emp_type")
#    emp_status = get_session(request, "s_rep_emp_status")
#    #i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_rep_idate")), "%Y-%m-%d %H:%M")
#    #e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_rep_edate")), "%Y-%m-%d %H:%M")
#    i_date = get_session(request, "s_rep_emp_idate")
#    e_date = get_session(request, "s_rep_emp_edate")
#    active = get_session(request, "s_rep_emp_active")
#
#    #kwargs = {"ini_date__range": (i_date, e_date)}
#    kwargs = {}
#    if emp != "":
#        kwargs["name__unaccent__icontains"] = emp
#    if emp_type != "":
#        kwargs["employee_type"] = emp_type
#    if active != "":
#        kwargs["inactive"] = True if active == "0" else False
#
#    res = []
#    emp_list = Employee.objects.filter(**kwargs)
#    status = TimetableStatus.objects.all()
#    for emp in emp_list:
#        res_dic = {"name": emp.name, "dni": emp.dni}
#        append = False
#        res_dic["status"] = []
#        for s in status:
#            if (emp_status == "") or (emp_status == str(s.id)):
#                hours, minutes = emp.assigned_by_type(i_date, e_date, s, cli)
#                if hours > 0 or minutes > 0:
#                    res_dic["status"].append({"name": s.name, "hours": hours, "minutes": minutes})
#                    append = True
#        if append:
#            h, m = emp.assigned_by_type(i_date, e_date)
#            res_dic["total_hours"] = h
#            res_dic["total_minutes"] = m
#            res.append(res_dic)
#    return res
#    #return Assistance.objects.filter(**kwargs)
#
#@group_required("admins",)
#def report(request):
#    init_session_date(request, "s_rep_idate")
#    init_session_date(request, "s_rep_edate")
#    return render(request, "report/report.html", {"items": []})
#    #return render(request, "report/report.html", {"items": get_report(request)})
#
#@group_required("admins",)
#def report_clients(request):
#    init_session_date(request, "s_rep_idate")
#    init_session_date(request, "s_rep_edate")
#    return render(request, "report/report-clients.html", {"items": []})
#    #return render(request, "report/report.html", {"items": get_report(request)})
#
#@group_required("admins",)
#def report_assistances(request):
#    init_session_date(request, "s_rep_idate")
#    init_session_date(request, "s_rep_edate")
#    return render(request, "report/report-assistances.html", {"items": []})
#
#@group_required("admins",)
#def report_clients_list(request):
#    item_list = get_report(request)
#    return render(request, "report/report-clients-list.html", {"items": item_list, "duration": get_total_duration(item_list)})
#
#@group_required("admins",)
#def report_assistances_list(request):
#    item_list = get_assistances_report(request)
#    return render(request, "report/report-assistances-list.html", {"items": item_list, "duration": get_total_duration(item_list)})
#
#@group_required("admins",)
#def report_clients_search(request, clients=""):
#    set_session(request, "s_rep_cli", get_param(request.GET, "s_rep_cli"))
#    set_session(request, "s_rep_idate", get_param(request.GET, "s_rep_idate"))
#    set_session(request, "s_rep_edate", get_param(request.GET, "s_rep_edate"))
#    set_session(request, "s_rep_cli_active", get_param(request.GET, "s_rep_cli_active"))
#    item_list = get_report(request)
#    return render(request, "report/report-clients-list.html", {"items": item_list,})
#
#@group_required("admins",)
#def report_assistances_search(request, clients=""):
#    set_session(request, "s_rep_emp", get_param(request.GET, "s_rep_emp"))
#    set_session(request, "s_rep_cli", get_param(request.GET, "s_rep_cli"))
#    set_session(request, "s_rep_cli_qr", get_param(request.GET, "s_rep_cli_qr"))
#    set_session(request, "s_rep_idate", get_param(request.GET, "s_rep_idate"))
#    set_session(request, "s_rep_edate", get_param(request.GET, "s_rep_edate"))
#    item_list = get_assistances_report(request)
#    return render(request, "report/report-assistances-list.html", {"items": item_list, "duration": get_total_duration(item_list),})
#    #return render(request, "report/report-list.html", {"items": item_list, "duration": get_total_duration(item_list)})
#
#@group_required("admins",)
#def report_export(request):
#    from datetime import datetime
#    from zoneinfo import ZoneInfo
#    header = ['Cliente', 'Empleado', 'Fecha de inicio', 'Fecha de fin', 'Duración del servicio', 'Finalizada']
#    values = []
#    items = get_assistances_report(request)
#    for item in items:
#        ini_date = item.ini_date.astimezone(ZoneInfo("Atlantic/Canary"))
#        idate = ini_date.strftime("%d-%m-%Y %H:%M")
#        end_date = item.end_date.astimezone(ZoneInfo("Atlantic/Canary"))
#        edate = end_date.strftime("%d-%m-%Y %H:%M")
#        finish = "Si" if item.finish else "No"
#        client = item.client.name if item.client != None else ""
#        emp = item.employee.name if item.employee != None else ""
#        row = [client, emp, idate, edate, item.duration, finish]
#        values.append(row)
#    return csv_export(header, values, "empleados")
#
#@group_required("admins",)
#def report_export_emp(request):
#    header = ['Empleado', 'DNI', 'Tipo', 'Horas asignadas', 'Horas', 'Minutos']
#    values = []
#    items = get_employees_report(request)
#    for item in items:
#        emp = item["name"]
#        dni = item["dni"]
#        total = item["total_hours"]
#        for s in item["status"]:
#            row = [emp, dni, s["name"], f'{s["hours"]} horas y {s["minutes"]} minutos', s['hours'], s["minutes"]]
#            #row = [emp, dni, s["name"], f'{s["hours"]} horas y {s["minutes"]} minutos', total]
#            values.append(row)
#    return csv_export(header, values, "empleados")
#
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
#
#@group_required("admins",)
#def report_search_cli(request):
#    try:
#        value = get_param(request.GET, "value")
#        items = Client.objects.filter(name__unaccent__icontains=value) if value != "" else []
#        return render(request, "report/report-search-cli.html", {'items': items, 'value':value})
#    except Exception as e:
#        return render(request, "error_exception.html", {'exc':show_exc(e)})
#
#@group_required("admins",)
#def report_employees(request):
#    init_session_date(request, "s_rep_emp_idate")
#    init_session_date(request, "s_rep_emp_edate")
#    set_session(request, "s_rep_emp", "")
#    set_session(request, "s_rep_emp_type", "")
#    context = {"items": [], 'emp_types': EmployeeType.objects.all(), 'status': TimetableStatus.objects.all()}
#    return render(request, "report/report-employees.html", context)
#
#@group_required("admins",)
#def report_employees_list(request):
#    item_list = get_employees_report(request)
#    return render(request, "report/report-employees-list.html", {"items": item_list, 'status': TimetableStatus.objects.all()})
#
#@group_required("admins",)
#def report_employees_search(request, clients=""):
#    set_session(request, "s_rep_emp", get_param(request.GET, "s_rep_emp"))
#    set_session(request, "s_rep_emp_cli", get_param(request.GET, "s_rep_emp_cli"))
#    set_session(request, "s_rep_emp_type", get_param(request.GET, "s_rep_emp_type"))
#    set_session(request, "s_rep_emp_status", get_param(request.GET, "s_rep_emp_status"))
#    set_session(request, "s_rep_emp_idate", get_param(request.GET, "s_rep_emp_idate"))
#    set_session(request, "s_rep_emp_edate", get_param(request.GET, "s_rep_emp_edate"))
#    set_session(request, "s_rep_emp_active", get_param(request.GET, "s_rep_emp_active"))
#    item_list = get_employees_report(request)
#    return render(request, "report/report-employees-list.html", {"items": item_list, 'status': TimetableStatus.objects.all()})
# 
'''
    EMPLOYEES
'''
@group_required("admins",)
def employee(request, obj_id):
    if "s_employee_idate" not in request.session:
        idate = datetime.today().replace(day=1)
        set_session(request, "s_employee_idate", idate.strftime("%Y-%m-%d"))
    else:
        idate = get_session(request, "s_employee_idate")
    if "s_employee_edate" not in request.session:
        idate = datetime.today().replace(day=1)
        last_day = calendar.monthrange(idate.year, idate.month)[1]
        edate = idate.replace(day=last_day)
        set_session(request, "s_employee_edate", edate.strftime("%Y-%m-%d"))
    else:
        edate = get_session(request, "s_employee_edate")
    emp = get_or_none(Employee, obj_id)
    client_list = emp.clients_timetable(idate, edate)
    return render(request, "employee/clients.html", {"obj": emp, "client_list": client_list})

@group_required("admins",)
def employee_search(request):
    obj_id = get_param(request.GET, "obj_id")
    set_session(request, "s_employee_idate", get_param(request.GET, "s_employee_idate"))
    set_session(request, "s_employee_edate", get_param(request.GET, "s_employee_edate"))
    return redirect(reverse('employee', kwargs={'obj_id': obj_id}))

@group_required("admins",)
def employee_search_client(request):
    try:
        value = get_param(request.GET, "value")
        obj = get_or_none(Employee, get_param(request.GET, "obj_id"))
        items = []
        if value != "":
            items = Client.objects.filter(name__unaccent__icontains=value)
        return render(request, "employee/client-search-list.html", {'items': items, 'obj': obj, 'value':value})
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

@group_required("admins",)
def employee_form_timetable(request):
    obj = get_or_none(Employee, get_param(request.GET, "obj_id"))
    if obj != None:
        client = get_or_none(Client, get_param(request.GET, "client_id"))
        days = request.GET.getlist("day")
        ini = get_param(request.GET, "ini")
        end = get_param(request.GET, "end")
        for day in days:
            ClientTimetable.objects.create(client=client, employee=obj, day=day, ini=ini, end=end)
    return redirect(reverse('employee', kwargs={'obj_id': obj.id}))
    #return render(request, "employees/employees-form-timetable.html", {'obj': obj, 'client_list': Client.objects.all()})

@group_required("admins",)
def employee_form_timetable_remove(request, obj_id):
    obj = get_or_none(ClientTimetable, obj_id)
    emp = None
    if obj != None:
        emp = obj.employee
        obj.delete()
    return redirect(reverse('employee', kwargs={'obj_id': emp.id}))


'''
    INCIDENTS
'''
def get_incidents(request):
    i_date = datetime.strptime("{} 00:00".format(get_session(request, "s_inc_idate")), "%Y-%m-%d %H:%M")
    e_date = datetime.strptime("{} 23:59".format(get_session(request, "s_inc_edate")), "%Y-%m-%d %H:%M")
    status = get_session(request, "s_inc_status")
    emp = get_session(request, "s_inc_emp")

    kwargs = {"creation_date__range": (i_date, e_date),}
    if status != "": 
        kwargs['closed'] = True if status == "True" else False
    if emp != "": 
        user_list = [item.user for item in Employee.objects.filter(name__unaccent__icontains=emp)]
        kwargs['owner__in'] = user_list
    return Incident.objects.filter(**kwargs)

@group_required("admins",)
def incidents(request):
    init_session_date(request, "s_inc_idate")
    init_session_date(request, "s_inc_edate")
    set_session(request, "s_inc_status", "False")
    return render(request, "incidents/incidents.html", {"items": get_incidents(request)})

@group_required("admins",)
def incidents_list(request):
    item_list = get_incidents(request)
    return render(request, "incidents/incidents-list.html", {"items": item_list})

@group_required("admins",)
def incidents_search(request):
    set_session(request, "s_inc_idate", get_param(request.GET, "s_inc_idate"))
    set_session(request, "s_inc_edate", get_param(request.GET, "s_inc_edate"))
    set_session(request, "s_inc_status", get_param(request.GET, "s_inc_status"))
    set_session(request, "s_inc_emp", get_param(request.GET, "s_inc_emp"))
    item_list = get_incidents(request)
    return render(request, "incidents/incidents-list.html", {"items": item_list,})

@group_required("admins",)
def incidents_form(request):
    obj = get_or_none(Incident, get_param(request.GET, "obj_id"))
    if obj == None:
        return render(request, "error_exception.html", {'exc': 'Object not found!'})
    return render(request, "incidents/incidents-form.html", {'obj': obj,})
