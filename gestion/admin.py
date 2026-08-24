from django.contrib import admin
from .models import *


class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "island", "zone"]

class ClientAdmin(admin.ModelAdmin):
    list_per_page = 500

class ClientGradeAdmin(admin.ModelAdmin):
    list_display = ["name",]

class ClientTypeAdmin(admin.ModelAdmin):
    list_display = ["name",]

class ClientInactiveTypeAdmin(admin.ModelAdmin):
    list_display = ["name",]

class ClientStoppedTypeAdmin(admin.ModelAdmin):
    list_display = ["name",]

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["name", "dni", "pin"]

class EmployeeTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "amount", "payer"]

class PayerAdmin(admin.ModelAdmin):
    list_display = ["name"]

class IslandAdmin(admin.ModelAdmin):
    list_display = ["name",]

class SelfEmployedTypeAdmin(admin.ModelAdmin):
    list_display = ["name",]

class TimetableStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "color", "calc"]


admin.site.register(City, CityAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(ClientGrade, ClientGradeAdmin)
admin.site.register(ClientInactiveType, ClientInactiveTypeAdmin)
admin.site.register(ClientType, ClientTypeAdmin)
admin.site.register(ClientStoppedType, ClientStoppedTypeAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(EmployeeType, EmployeeTypeAdmin)
admin.site.register(Payer, PayerAdmin)
admin.site.register(Assistance)
admin.site.register(Incident)
admin.site.register(Island, IslandAdmin)
admin.site.register(SelfEmployedType, SelfEmployedTypeAdmin)
admin.site.register(TimetableStatus, TimetableStatusAdmin)
admin.site.register(Zone)

#class FacilityTypeAdmin(admin.ModelAdmin):
#    list_display = ('code', 'name', 'order', 'operation_time', 'dashboard')
#
#class TruckTypeAdmin(admin.ModelAdmin):
#    list_display = ('brand', 'model', 'year')
#
#
#class WasteInFacilityAdmin(admin.ModelAdmin):
#    list_display = ('code', 'facility', 'waste', 'filling_degree', 'toRoute')
#    list_filter = ('facility',)
#
#admin.site.register(FacilityType, FacilityTypeAdmin)
##admin.site.register(Priority, PriorityAdmin)
#admin.site.register(TruckType, TruckTypeAdmin)
#admin.site.register(WasteInFacility, WasteInFacilityAdmin)
#
