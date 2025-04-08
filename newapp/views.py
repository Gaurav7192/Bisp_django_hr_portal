from django.shortcuts import render,redirect
from .models import *
from django.http import HttpResponseNotFound
from django.contrib.auth.hashers import make_password
from django.contrib import messages
import time


# Create your views here.
def home(request):
    return render(request,'index.html')
def index2(request):
    return render(request,'index2.html')

def dashboard_v1(request):
    return render(request, 'index.html')

def dashboard_v2(request):
    return render(request, 'index2.html')



def dashboard_v3(request):
    return render(request, 'index3.html')

def widgets(request):
    return render(request, 'widgets.html')

def layouts(request):
    return render(request, template_name='top-nav.html')
def top_layout(requset):
    return render(request, template_name='top-nav-sidebar.html')
def boxed(request):
    return render(request, template_name='boxed.html')

def fixed_sidebar(request):
    return render(request, template_name='fixed-sidebar.html')
def login_v1(request):
    return render(request,template_name='login.html')
def registration_v1(request):
    return render(request,template_name='register.html')










def fixed_sidebar_custom(request):
    return render(request,'fixed-sidebar-custom.html')

def fixed_topnav(request):
    return  render(request,'fixed-topnav.html')

def fixed_footer(request):
    return render(request,'fixed-footer.html')

def collapsed(request):
    return render(request,'collapsed-sidebar.html')

def chartjs(request):
    return render(request,'chartjs.html')

def flot(request):
    return render(request,'flot.html')

def inline(request):
    return render(request,'inline.html')

def uplot(request):
    return render(request,'uplot.html')

def generalhtml(request):
    return render(request,'general.html')

def icons(request):
    return render(request,'icons.html')

def buttonHTML(request):
    return render(request, 'buttons.html')

def sliders(request):
    return render(request,'sliders.html')

def model(request):
    return render(request, 'modals.html')

def navbar(request):
    return render(request,'navbar.html')

def timeline(request):
    return render(request,'timeline.html')

def ribbon(request):
    return render(request,'ribbons.html')

def generalform(request):
    return render(request,'general.html')

def advform(request):
    return render(request,'advanced.html')

def editors(request):
    return render(request,'editors.html')

def validation(request):
    return render(request,'validation.html')

def simpletable(request):
    return render(request,'simple.html')

def datatable(request):
    return render(request,'data.html')

def jsgrid(request):
    return render(request,'jsgrid.html')

def gallery(request):
    return render(request, 'gallery.html')


def calender(request):
    return  render(request,'calendar.html')

def kanban(request):
    return render(request, 'kanban.html')

def error404(request):
    return HttpResponseNotFound(render(request, '404.html'))

def error500(request):
    # This will raise a server error intentionally
    return render(request,template_name='500.html')

def about(request):
    return  render(request,'about.html')

def Side_Navbar(request):
    return render(request,'Side_Navbar.html')
def mailbox(request):
    return render(request , "mailbox.html")
def compose(request):
    return render(request, "compose.html")
def read_mail(request):
    return render(request,template_name="read-mail.html")
def invoice(request):
    return render(request,"invoice.html")
def profile_view(request):
    return render(request, 'profile.html')
def e_commerce(request):
    return render(request,"e-commerce.html")
# def login(request):
#     if request.method =="POST":
#         data=request.POST
#         email=data.get(Email)
#         password=data.get(Password)
#         remeber=data.get(remember)



def register(request):
    redirect('widgets')
    if request.method == "POST":
        name = request.POST.get('Rname')
        email = request.POST.get('Remail')
        password = request.POST.get('Password')
        confirm_password = request.POST.get('Retype_password')
        usertype=request.POST.get("Rcheck")
        print(usertype)
        if password != confirm_password:
            messages.success(request, 'pass and conform password should same')


        user = registers(rname=name, remail=email, rpassword=password, admin= bool(usertype))
        user.save()
        messages.success(request, "Registration successful! Please log in.")
        return redirect('user_login')
    return render(request, 'register.html')



def user_login(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        DataEmail = Data.objects.filter(remail=email).first() #quertyset

        if DataEmail:
            print(DataEmail.Email, DataEmail.Password)

            # Directly compare passwords (since they're stored in plain text)
            if password == DataEmail.Password:

                request.session['user_id'] = DataEmail.id
                request.session['email'] = DataEmail.Email # stored id and email in a session

                messages.success(request, f"Login successful! Welcome! {DataEmail.Full_name}")
                if DataEmail.admin:
                     # messages.success(request, f"Login successful! Welcome {DataEmail.Full_name}.")
                     return redirect('dashboard_v1')  # Redirect to dashboard
                else:
                    # messages.success(request, f"Login successful! Welcome Employee {DataEmail.Full_name}.")
                    return redirect('Sindex')
            else:
                messages.error(request, "Invalid password")
        else:
            messages.error(request, "User not found")

    return render(request, 'login.html')
#
# def add(request):
#     if request.method == "POST":
#         name = request.POST.get("Name")
#         email = request.POST.get("email")
#         action = request.POST.get("action")
#         Students = Student.objects.all()
#
#         if action == "add":
#
#             Student.objects.create(name=name, email=email)
#             return render(request, 'home.html', {"Students": Students})
#
#         elif action == "delete":
#             #delete from student where email={{}}
#             Student.objects.filter(email=email).delete()
#             return render(request, 'home.html', {"Students": Students})
#
#         elif action == "update":
#             #update student set={{name}} where email={{}}
#             Student.objects.filter(email=email).update(name=name)
#             return render(request, 'home.html', {"Students": Students})




def pro(request):

    if request.method == "POST":
        P_Name = request.POST.get("P_name")
        Quan = request.POST.get("Quan")
        Price = request.POST.get("Price")
        action=request.POST.get("action")
        Product = product.objects.all()

        if action == "add":

            product.objects.create(p_name=P_Name,  Quantity=Quan, price=Price)
            return render(request, 'result.html', {"products": Product})

        elif action == "delete":
            #delete from student where email={{}}
            product.objects.filter(p_name=P_Name).delete()
            return render(request, 'result.html', {"products": Product})

        elif action == "update":
            #update student set={{name}} where email={{}}
            product.objects.filter(p_name=P_Name).update(price=Price)
            return render(request, 'result.html', {"products": Product})


import time
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import registers


def register_v2(request):
    if request.method == "POST":
        name = request.POST.get('Rname')
        email = request.POST.get('Remail')
        password = request.POST.get('Password')
        confirm_password = request.POST.get('Retype_password')
        usertype = request.POST.get("Rcheck")
        print(usertype)

        if password != confirm_password:
            messages.error(request, 'Password and Confirm Password should be the same.')
            time.sleep(2)  # Add 2-second delay
            return redirect('register')

        user = registers(rname=name, remail=email, rpassword=password, admin=bool(usertype))
        user.save()
        messages.success(request, "Registration successful! Please log in.")
        time.sleep(2)  # Add 2-second delay
        return redirect('user_login')

    return render(request, 'register.html')
def projects(request):
    return render(request ,"projects")


def ab1(request):
    return render(request ,"1.html")