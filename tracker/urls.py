from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('dashboard/export.xlsx', views.export_dashboard_excel, name='export_dashboard_excel'),
    path('timesheets/', views.timesheets, name='timesheets'),
    path('timesheets/submit/', views.submit_timesheet, name='submit_timesheet'),
    path('timesheets/<int:pk>/edit/', views.edit_timesheet, name='edit_timesheet'),
    path('timesheets/<int:pk>/delete/', views.delete_timesheet_record, name='delete_timesheet_record'),
    path('entries/add/', views.add_entry, name='add_entry'),
    path('entries/<int:pk>/delete/', views.delete_entry, name='delete_entry'),
    path('projects/add/', views.add_project, name='add_project'),
    path('console/', views.admin_console, name='admin_console'),
    path('console/users/create/', views.create_user, name='create_user'),
    path('console/users/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('console/users/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('console/margins/', views.save_margins, name='save_margins'),
]
