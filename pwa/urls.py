from django.urls import path
from pwa import views


urlpatterns = [
    path('', views.index, name="pwa-home"),
    path('home/', views.index, name="pwa-home"),
    path('login/', views.pin_login, name="pwa-login"),
    path('logoff/', views.pin_logout, name="pwa-logout"),

    # EMPLOYEES
    path('employee/', views.employee_home, name="pwa-employee"),
    path('employee/qr-scan', views.employee_qr_scan, name="pwa-qr-scan"),
    path('employee/qr-scan-finish', views.employee_qr_scan_finish, name="pwa-qr-scan-finish"),
    path('employee/qr-read', views.employee_qr_read, name="pwa-qr-read"),
    path('employee/qr-finish', views.employee_qr_finish, name="pwa-qr-finish"),
    path('employee/code-read', views.employee_code_read, name="pwa-code-read"),
    path('employee/code-finish', views.employee_code_finish, name="pwa-code-finish"),
    #path('employee/qr-finish/<int:obj_id>', views.employee_qr_finish, name="pwa-qr-finish"),
    path('employee/client/<int:obj_id>', views.employee_client, name="pwa-employee-client"),
    path('employee/client/finish/<int:obj_id>', views.employee_client_finish, name="pwa-employee-client-finish"),
    path('employee/client-list/', views.employee_client_list, name="pwa-employee-client-list"),
        
    # INCIDENTS
    path('incidents/incidents', views.incidents, name="pwa-incidents"),
    path('incidents/incidents/add', views.incidents_add, name="pwa-incidents-add"),
    path('incidents/incidents/save', views.incidents_save, name="pwa-incidents-save"),
]

