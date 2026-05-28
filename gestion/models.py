from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from django.utils.translation import gettext_lazy as _ 
from django.utils import timezone

import datetime


def sub_hours(hour1, hour2):
    """
    Resta dos objetos time y devuelve la diferencia como timedelta
    """
    now = datetime.datetime.now().date()

    datetime1 = datetime.datetime.combine(now, hour1)
    datetime2 = datetime.datetime.combine(now, hour2)

    diff = datetime1 - datetime2
    return int(diff.total_seconds() / 60)

def hours_mins(minutes):
    hours=0
    if minutes > 59:
        hours += minutes // 60
        minutes = minutes % 60
    return hours, minutes

'''
    AUX
'''
class Zone(models.Model):
    name = models.CharField(max_length=200, verbose_name = _('Razón Social'), default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Zona')
        verbose_name_plural = _('Zonas')
        ordering = ["name"]

class Island(models.Model):
    name = models.CharField(max_length=200, verbose_name = _('Nombre'), default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Isla')
        verbose_name_plural = _('Islas')
        ordering = ["name"]

class City(models.Model):
    name = models.CharField(max_length=200, verbose_name = _('Nombre'), default="")
    #island = models.ForeignKey(Island, verbose_name=_('Isla'), on_delete=models.SET_NULL, null=True, related_name="cities")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Municipio')
        verbose_name_plural = _('Municipios')
        ordering = ["name"]

'''
    EMPLOYEE
'''
class EmployeeType(models.Model):
    amount = models.FloatField(default=0, verbose_name=_('Cuantia'));
    name = models.CharField(max_length=200, verbose_name = _('Nombre'), default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Tipo de empleado')
        verbose_name_plural = _('Tipos de empleado')
        ordering = ["name"]

class Employee(models.Model):
    inactive = models.BooleanField(default=False, verbose_name=_('Desactivado'));
    pin = models.CharField(max_length=20, verbose_name = _('PIN'), default="")
    dni = models.CharField(max_length=20, verbose_name = _('DNI'), default="")
    name = models.CharField(max_length=200, verbose_name = _('Razón Social'), default="")
    phone = models.CharField(max_length=50, verbose_name = _('Teléfono de contacto'), null=True, default = '0000000000')
    email = models.EmailField(verbose_name = _('Email de contacto'), default="", null=True)
    user = models.OneToOneField(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True, related_name='employee')
    zone = models.ForeignKey(Zone, verbose_name=_('Zona'), on_delete=models.SET_NULL, null=True, related_name="employees")
    employee_type = models.ForeignKey(EmployeeType,verbose_name=_('Tipo'),on_delete=models.SET_NULL,null=True,related_name="employees")

    def __str__(self):
        return self.name

    def save_user(self):
        if self.user == None:
            self.user = User.objects.create_user(username=self.email, email=self.email)
            self.save()
            group = Group.objects.get(name='employees') 
            group.user_set.add(self.user)
        else:
            self.user.username = self.email
            self.user.save()

    def worked_time(self, ini_date, end_date):
        try:
            idate = "{} 00:00".format(ini_date)
            edate = "{} 23:59".format(end_date)
            item_list = self.assistances.filter(ini_date__gte=idate, end_date__lte=edate)
            #item_list = self.assistances.filter(ini_date__gte=ini_date, end_date__lte=end_date)
            hours = 0
            minutes = 0
            for item in item_list:
                if item.finish:
                    diff = item.end_date - item.ini_date
                    days, seconds = diff.days, diff.seconds
                    hours += seconds // 3600
                    minutes += (seconds % 3600) // 60
                    #hours = days * 24 + seconds // 3600
                    #seconds = seconds % 60
            if minutes > 59:
                hours += minutes // 60
                minutes = minutes % 60
            return hours, minutes
            #return "{}:{}".format(hours, minutes) 
            #return "{} horas y {}  minutos".format(hours, minutes) 
        except Exception as e:
            print(e)
            return 0, 0

    def client_worked_time(self, client, ini_date, end_date):
        idate = "{} 00:00".format(ini_date)
        edate = "{} 23:59".format(end_date)
        item_list = self.assistances.filter(ini_date__gte=idate, end_date__lte=edate, client__id=client)
        hours = 0
        minutes = 0
        for item in item_list:
            if item.finish:
                diff = item.end_date - item.ini_date
                days, seconds = diff.days, diff.seconds
                hours += seconds // 3600
                minutes += (seconds % 3600) // 60
                #hours = days * 24 + seconds // 3600
                #seconds = seconds % 60
        if minutes > 59:
            hours += minutes // 60
            minutes = minutes % 60
        return hours, minutes
 
    def client_work(self, client, ini_date, end_date):
        idate = "{}".format(ini_date)
        edate = "{}".format(end_date)
        item_list = self.timetables.filter(client__id=client, date__range=(idate, edate), status__calc=True)
        mins = 0
        for item in item_list:
            try:
                mins += sub_hours(item.end, item.ini)
            except Exception as e:
                mins += 0
        return hours_mins(mins)
 
    def clients_timetable(self, idate, edate):
        dic = {}
        #for item in self.timetables.all():
        for item in self.timetables.filter(date__range = (idate, edate)):
            if item.client != None:
                if item.client.name not in dic.keys():
                    dic[item.client.name] = []
                dic[item.client.name].append({"day":item.week_day,"ini":item.ini,"end":item.end,"id":item.id,"client":item.client.id})
        return dic

    def client_list(self, qr_access=False):
        #if qr_access:
        #    return self.timetables.filter(client__qr_access=qr_access).order_by("client").distinct("client")
        return self.timetables.filter(date__gte=datetime.datetime.today(), client__qr_access=qr_access).order_by("client").distinct("client")

    def assigned_by_type(self, ini_date, end_date, status=None):
        idate = "{}".format(ini_date)
        edate = "{}".format(end_date)

        if status is not None:
            item_list = self.timetables.filter(status=status, date__range=(idate, edate))
        else:
            item_list = self.timetables.filter(date__range=(idate, edate))

        mins = 0
        for item in item_list:
            try:
                mins += sub_hours(item.end, item.ini)
            except Exception as e:
                mins += 0
        return hours_mins(mins)
 
    def get_categories(self):
        return [item.employee_type for item in self.categories.all()]

    class Meta:
        verbose_name = _('Empleado')
        verbose_name_plural = _('Empleados')
        ordering = ["name"]

class EmployeeCategory(models.Model):
    employee = models.ForeignKey(Employee,verbose_name=_('Empleado'),on_delete=models.CASCADE,null=True,related_name="categories")
    employee_type=models.ForeignKey(EmployeeType,verbose_name=_('Tipo'),on_delete=models.SET_NULL,null=True,related_name="categories")

    #def __str__(self):
    #    return self.name

    class Meta:
        verbose_name = _('Categoría empleado')
        verbose_name_plural = _('Categorías empleados')


'''
    CLIENTS
'''
class ClientType(models.Model):
    name = models.CharField(max_length=200, verbose_name = _('Nombre'), default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Tipo cliente')
        verbose_name_plural = _('Tipos de cliente')
        ordering = ["name"]

class ClientGrade(models.Model):
    name = models.CharField(max_length=200, verbose_name = _('Nombre'), default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Grado')
        verbose_name_plural = _('Grados')
        ordering = ["name"]

def upload_form_qr(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "clients/qr/%s" % (instance.id)
    return '/'.join(['%s' % (folder), datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class Client(models.Model):
    qr_access = models.BooleanField(default=False, verbose_name=_('Acceso QR'));
    inactive = models.BooleanField(default=False, verbose_name=_('Desactivado'));
    amount = models.FloatField(default=0, verbose_name=_('Cuantia'));
    exp = models.CharField(max_length=200, verbose_name = _('Número de expediente'), default="")
    code = models.CharField(max_length=200, verbose_name = _('Code'), default="")
    name = models.CharField(max_length=200, verbose_name = _('Razón Social'), default="")
    phone = models.CharField(max_length=50, verbose_name = _('Teléfono de contacto'), null=True, default='0000000000')
    email = models.EmailField(verbose_name = _('Email de contacto'), default="", null=True)
    address = models.TextField(verbose_name = _('Dirección'), null=True, default='')
    #city = models.TextField(verbose_name = _('Municipio'), null=True, default='')
    observations = models.TextField(verbose_name = _('Observaciones'), null=True, default='')
    date = models.DateField(default=timezone.now, null=True, verbose_name=_('Inicio'))
    date_inactive = models.DateField(default=datetime.date(1900, 1, 1), null=True, verbose_name=_('Inicio'))
    obs_inactive = models.TextField(verbose_name = _('Observaciones inactivo'), null=True, default='')
    qr = models.ImageField(upload_to=upload_form_qr, blank=True, verbose_name="QR", help_text="Select file to upload")
    city = models.ForeignKey(City, verbose_name=_('Municipio'), on_delete=models.SET_NULL, null=True)
    client_type = models.ForeignKey(ClientType, verbose_name=_('Tipo'), on_delete=models.SET_NULL, null=True)
    #grade = models.ForeignKey(ClientGrade, verbose_name=_('Grado'), on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    @property
    def emp_assigned(self):
        return (self.timetables.count() > 0)

    def assigned_work(self):
        item_list = self.timetables.filter(client__id=self.id)
        mins = 0
        for item in item_list:
            try:
                mins += sub_hours(item.end, item.ini)
            except Exception as e:
                mins += 0
        return hours_mins(mins)
 
    def employees_id(self):
        return [item.employee.id for item in self.employees.all()]

    def emp_timetable(self):
        dic = {}
        for item in self.timetables.all():
            if item.client.name not in dic.keys():
                dic[item.client.name] = []
            dic[item.client.name].append({"day":item.week_day, "ini":item.ini, "end":item.end, "id":item.id, "client":item.client.id})
        return dic

    def emp_worked_time(self, emp, ini_date, end_date):
        idate = "{} 00:00".format(ini_date)
        edate = "{} 23:59".format(end_date)
        if emp != "":
            item_list = self.assistances.filter(ini_date__gte=idate, end_date__lte=edate, employee__id=emp)
        else:
            item_list = self.assistances.filter(ini_date__gte=idate, end_date__lte=edate)
        hours = 0
        minutes = 0
        for item in item_list:
            if item.finish:
                diff = item.end_date - item.ini_date
                days, seconds = diff.days, diff.seconds
                hours += seconds // 3600
                minutes += (seconds % 3600) // 60
                #hours = days * 24 + seconds // 3600
                #seconds = seconds % 60
        if minutes > 59:
            hours += minutes // 60
            minutes = minutes % 60
        return hours, minutes
 
    def emp_work(self, emp, ini_date, end_date):
        idate = "{}".format(ini_date)
        edate = "{}".format(end_date)
        if emp != "":
            item_list = self.timetables.filter(employee__id=emp, date__range=(idate, edate), status__calc=True)
        else:
            item_list = self.timetables.filter(date__range=(idate, edate), status__calc=True)
        mins = 0
        for item in item_list:
            try:
                mins += sub_hours(item.end, item.ini)
            except Exception as e:
                mins += 0
        return hours_mins(mins)
 
    def assigments(self):
        import json

        assigments = {}
        for item in self.timetables.all():
            ce = ClientEmployee.objects.filter(client=self, employee=item.employee).first()
            dic = {
                "timetable": item.id,
                "id": ce.id,
                "name": item.employee.name,
                "start": item.ini.strftime("%H:%M:%S"),
                "end": item.end.strftime("%H:%M:%S"),
                "status": ""
            }
            try:
                assigments[item.date.strftime("%Y-%m-%d")].append(dic)
            except:
                assigments[item.date.strftime("%Y-%m-%d")] = [dic]
        return assigments

    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')

class TimetableStatus(models.Model):
    calc = models.BooleanField(default=True, verbose_name=_('Suma al cálculo'));
    code = models.CharField(max_length=10, verbose_name=_('Código'))
    name = models.CharField(max_length=255, verbose_name=_('Nombre'))
    color = models.CharField(max_length=10, verbose_name=_('Color'), default="")

    class Meta:
        verbose_name = _('Estado horario')
        verbose_name_plural = _('Estados horarios')

class ClientTimetable(models.Model):
    day = models.IntegerField(verbose_name = _('Día'), default=0)
    date = models.DateField(verbose_name = _('Día'), default=timezone.now)
    ini = models.TimeField(max_length=10, verbose_name = _('Hora de inicio'), default=datetime.time(8,0,0))
    end = models.TimeField(max_length=10, verbose_name = _('Hora de fin'), default=datetime.time(8,0,0))
    client = models.ForeignKey(Client,verbose_name=_('Cliente'),on_delete=models.SET_NULL,null=True,related_name="timetables")
    employee = models.ForeignKey(Employee,verbose_name=_('Empleado'),on_delete=models.SET_NULL,null=True,related_name="timetables")
    status = models.ForeignKey(TimetableStatus,verbose_name=_('Estado'),on_delete=models.SET_NULL,null=True)

    #def __str__(self):
    #    return self.name

    @property
    def week_day(self):
        wd = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        return wd[self.day]

    def get_in_same_day(self):
        return ClientTimetable.objects.filter(client=self.client, date=self.date)

    class Meta:
        verbose_name = _('Horario')
        verbose_name_plural = _('Horarios')
        ordering = ["day",]

class ClientEmployee(models.Model):
    client = models.ForeignKey(Client,verbose_name=_('Cliente'),on_delete=models.SET_NULL,null=True,related_name="employees")
    employee = models.ForeignKey(Employee,verbose_name=_('Empleado'),on_delete=models.SET_NULL,null=True,related_name="clients")

    class Meta:
        verbose_name = _('Empleado')
        verbose_name_plural = _('Empleados')
        ordering = ["client__name",]

def upload_client_file(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "clients/%s" % (instance.id)
    return '/'.join(['%s' % (folder), datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class ClientDoc(models.Model):
    doc = models.FileField(upload_to=upload_client_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    client = models.ForeignKey(Client, verbose_name="Documento", on_delete=models.CASCADE, null=True, related_name="docs")

    class Meta:
        verbose_name = "Documento de client"
        verbose_name_plural = "Documentos de cliente"

class ClientTypeAmount(models.Model):
    amount = models.FloatField(default=0, verbose_name=_('Cuantia'));
    client_type = models.ForeignKey(ClientType, verbose_name=_('Tipo'), on_delete=models.SET_NULL, null=True)
    client = models.ForeignKey(Client, verbose_name="Documento", on_delete=models.CASCADE, null=True, related_name="types")

    class Meta:
        verbose_name = "Tipo de cliente"
        verbose_name_plural = "Tipos de clientes"

class ClientInactiveType(models.Model):
    name = models.CharField(max_length=200, verbose_name = _('Nombre'), default="")

    class Meta:
        verbose_name = _('Motivo baja')
        verbose_name_plural = _('Motivos baja')

class ClientInactive(models.Model):
    date = models.DateField(default=datetime.date(1900, 1, 1), null=True, verbose_name=_('Inicio'))
    obs = models.TextField(verbose_name = _('Observaciones inactivo'), null=True, default='')
    itype = models.ForeignKey(ClientInactiveType,verbose_name=_('Tipo'),on_delete=models.SET_NULL,null=True)
    client = models.ForeignKey(Client,verbose_name=_('Cliente'),on_delete=models.SET_NULL,null=True,related_name="inactives")

    class Meta:
        verbose_name = _('Inactivo')
        verbose_name_plural = _('Inactivos')


'''
    ASSISTANCE
'''
class Assistance(models.Model):
    finish = models.BooleanField(default=False, verbose_name=_('Terminada'));
    ini_date = models.DateTimeField(default=timezone.now, null=True, verbose_name=_('Inicio'))
    end_date = models.DateTimeField(default=timezone.now, null=True, verbose_name=_('Fin'))
    client = models.ForeignKey(Client, verbose_name=_('Client'), on_delete=models.SET_NULL, null=True, related_name="assistances")
    employee = models.ForeignKey(Employee,verbose_name=_('Empleado'),on_delete=models.SET_NULL,null=True,related_name="assistances")

    @property
    def duration(self):
        edate = self.end_date.replace(second=0, microsecond=0) 
        idate = self.ini_date.replace(second=0, microsecond=0)
        diff = edate - idate
        days, seconds = diff.days, diff.seconds
        return (seconds // 60)
        #hours += seconds // 3600
        #minutes += (seconds % 3600) // 60
        #if minutes > 59:
        #    hours += minutes // 60
        #    minutes = minutes % 60
        #return hours, minutes
 
    class Meta:
        verbose_name = _('Asistencia')
        verbose_name_plural = _('Asistencias')

'''
    Incidents
'''
class Incident(models.Model):
    closed = models.BooleanField(default=False, verbose_name = _('Estado'))
    code = models.CharField(max_length=10, verbose_name=_('Código'))
    subject = models.CharField(max_length=255, verbose_name=_('Asunto'))
    description = models.TextField(verbose_name=_('Descripción'), default='', blank=True, null=True)
    creation_date = models.DateTimeField(default=timezone.now, verbose_name=_('Creado el'))
    closed_date = models.DateTimeField(default=datetime.datetime.max, blank=True, null=True, verbose_name=_('Cerrado el'))

    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False, verbose_name=_('Creada por'))

    @property
    def employee(self):
        return Employee.objects.filter(user=self.owner).first()

    class Meta:
        verbose_name = _('Incidente')
        verbose_name_plural = _('Incidentes')
        ordering = ['-creation_date']

    def __str__(self):
        return self.subject

