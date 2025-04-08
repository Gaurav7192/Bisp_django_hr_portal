
from django.urls import path
from . import views

urlpatterns = [
    path('ab',views.ab1,name='ab1'),

    path('home/', views.home, name='index'),
    path('index/', views.index2, name='index2'),
    path('dashboard-v1/', views.dashboard_v1, name='dashboard_v1'),
    path('dashboard-v2/', views.dashboard_v2, name='dashboard_v2'),
    path('dashboard-v3/', views.dashboard_v3, name='dashboard_v3'),
    path('widgets/', views.widgets, name='widgets'),

    path('layouts/', views.layouts, name='layouts'),
    path('top_layout/', views.top_layout, name='top_layout'),
    path('boxed/', views.boxed, name='boxed'),
    path('fixed-sidebar/', views.fixed_sidebar, name='fixed_sidebar'),

    # path('',views.register, name='register'),
    # Authentication
    # path('', views.user_login, name='user_login'),

    path('fixed-sidebar-custom/', views.fixed_sidebar_custom, name='fixed_sidebar_custom'),
    path('fixed-topnav/', views.fixed_topnav, name='fixed_topnav'),
    path('collapsed-sidebar/', views.collapsed, name='collapsed_sidebar'),
    path('fixed-footer/', views.fixed_footer, name='fixed_footer'),
    path('chartjs/', views.chartjs, name='chartjs'),
    path('flot/', views.flot, name='flot'),
    path('inline/', views.inline, name='inline'),
    path('uplot/', views.uplot, name='uplot'),
    path('general/', views.generalhtml, name='generalhtml'),
    path('icons/', views.icons, name='icons'),
    path('buttons/', views.buttonHTML, name='buttons'),
    path('sliders/', views.sliders, name='sliders'),
    path('modals/', views.model, name='modals'),
    path('navbar/', views.navbar, name='navbar'),
    path('timeline/', views.timeline, name='timeline'),
    path('ribbons/', views.ribbon, name='ribbons'),
    path('general/', views.generalform, name='generalform'),
    path('advform/', views.advform, name='advform'),
    path('advanced-forms/', views.advform, name='advanced_forms'),
    path('editors/', views.editors, name='editors'),
    path('validation/', views.validation, name='validation'),
    path('simpletable/', views.simpletable, name='simpletable'),
    path('data-tables/', views.datatable, name='datatable'),
    path('jsgrid/', views.jsgrid, name='jsgrid'),
   # path('login/', views.login, name='login'),
    path('calendar/', views.calender, name='calendar'),
    path('compose',views.compose,name='compose'),
    path('invoice',views.invoice,name='invoice'),
path('profile/', views.profile_view, name='profile'),
    path('e-commerce',views.e_commerce,name="e-commerce"),
    path('read-mail',views.read_mail,name='read-mail'),
    path('mailbox',views.mailbox,name='mailbox'),
    path('about/', views.about, name='about'),
    path('gallery/', views.gallery, name='gallery'),
    path('kanban/', views.kanban, name='kanban'),
    path('error500',views.error500,name='error500'),
    path('error404/', views.error404, name='error404'),
    path('Slidebar/',views.Side_Navbar,name='Side_Navbar'),

    path('projects',views.projects,name='projects'),
]

    # path("a/",views.a,name='a'),

#     "dashboard_v1": "index.html",
#     "dashboard_v2": "index2.html",
#     "dashboard_v3": "index3.html",
#     "widget": "widgets.html",
#     "top_nav": "layout/top-nav.html",
#     "top_nav_sidebar": "layout/top-nav-sidebar.html",
#     "box": "layout/boxed.html",
#     "fixed_sidebar": "layout/fixed-sidebar.html",
#     "fixed_sidebar_custom": "layout/fixed-sidebar-custom.html",
#     "fixed_topnav": "layout/fixed-topnav.html",
#     "fixed_footer": "layout/fixed-footer.html",
#     "collapsed": "layout/collapsed-sidebar.html",
#     "chartjs": "charts/chartjs.html",
#     "flot

