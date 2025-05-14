from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
urlpatterns = [
    # path('', home_view, name='home'),
    # path('about/', about_view, name='about'),


#     path('d2/<int:id>/',d2, name='d2l'),
    # path('contact/', contact_view, name='contact'),
    path('apply_leave/<int:user_id>/',apply_leave, name='apply_leave'),
  #  path('forgot_password/',forgot_password, name='forgot_password'),
    path('add_project/<int:user_id>',add_project_view,name='add_project'),
    path('project/<int:user_id>',project, name='project'),
    path('login/',login_view, name='login'),
    path('d1/<int:id>/', d1, name='d1'),
    path('d2/<int:id>/', d2, name='d2'),

path('team_task_report/<int:user_id>/', team_task_report, name='team_task_report'),
    #path('create_project/',create_project, name='create_project'),
    path('apply_leave/',apply_leave,name='apply_leave'),
path('add_task/<int:user_id>/', add_task_view, name='add_task'),
    path('task_list_view/<int:user_id>/',task_list_view, name='task_list_view'),
path('logout/',auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('',login_view, name='login'),
# urls.py


    path('leave-type/<int:leave_type_id>/details/', leave_type_detail_view, name='leave_type_detail'),

    path('employee_registration/<int:id>',employee_registration, name='employee_registration'),
 #   path('employee_registration/<int:id>/',employee_registration,name='employee_registration'),
    path('', login_view, name='login'),
path('update/<int:id>/', update_employee, name='update_employee'),
    path('delete/<int:id>/', delete_employee, name='delete_employee'),
    path('employee_list,',employee_list,name="employee_list"),
    path('add/', add_employee, name='add_employee'),
    path('update_employee',update_employee,name='update_employee'),
path('leave_record/<int:user_id>', leave_record_view, name='leave_record'),
    # path('update_employee/', update_employee, name='update_employee'),
    path('update_leaves_view',update_leaves_view,name='update_leaves_view'),
    path('update-leave-status/<int:user_id>', update_leave_status, name='update_leave_status'),
 path('leave_dashboard/<int:user_id>/', leave_dashboard, name='leave_dashboard'),
    path("update_timesheet/<int:user_id>/", update_timesheet, name="update_timesheet"),
path('task/update/<int:task_id>/',update_task_status_page, name='update_task_status_page'),
path('user_timesheet',user_timesheet,name='user_timesheet'),
    path('reset-password/',reset_password, name='reset_password'),
    path('manage_leave_department_role/', manage_leave_department_role, name='manage_leave_department_role'),
   # path('get_existing_data/<str:category>/',get_existing_data, name='get_existing_data'),
    path('leave-type-panel/', leave_type_panel, name='leave_type_panel'),
    path('add-leave-type/',add_leave_type, name='add_leave_type'),
    path('project_detail/<int:pk>/',project_detail_view, name='project_detail'),
path('project_edit/<int:project_id>/', project_edit_view, name='project_edit'),
    path('team_timesheet_record',team_timesheet_record,name='team_timesheet_record'),
    path('get-members/<int:project_id>/', get_project_members, name='get_project_members'),
#path('change-password/', change_password, name='change_password'),
path('update_profile/<int:user_id>',update_profile, name='update_profile'),
    path('image_timesheet/<int:user_id>',image_timesheet,name='image_timesheet'),
    path('image_timesheet_record/<int:user_id>',image_timesheet_record, name='image_timesheet_record'),
path('get-tasks/', get_tasks, name='get_tasks'),
    path('employee/profile/<int:emp_id>/', employee_profile, name='employee_profile'),
    path('view_profile_history/<int:emp_id>/', view_profile_history, name='view_profile_history'),
    path('handbooks/<int:user_id>', handbook_view, name='handbook'),
    path('handbook_list/',handbook_list,name='handbook_list'),
    #path('handbooks/', handbook_panel, name='handbook_panel'),
    # path('handbooks/acknowledge/<int:handbook_id>/', acknowledge_handbook, name='acknowledge_handbook'),

    # Add history view URL here
   # path('employee/profile/history/<int:emp_id>/',employee_history, name='history_page_url'),

]


#     path('forgot-password/', forgot_password, name='forgot_password'),
#     path('verify-otp/', verify_otp, name='verify_otp'),
#     path('set-new-password/',set_new_password, name='set_new_password'),
# ]
