from django.contrib import admin
from .models import *


class ClientAdmin(admin.ModelAdmin):
    list_per_page = 500

class ClientTypeAdmin(admin.ModelAdmin):
    list_display = ["name",]

class EmployeeTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "amount"]

class TimetableStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "color"]


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientType, ClientTypeAdmin)
admin.site.register(Employee)
admin.site.register(EmployeeType, EmployeeTypeAdmin)
admin.site.register(Assistance)
admin.site.register(Incident)
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
