from typing import Any
from django.shortcuts import redirect, render
from django.views.generic import CreateView
from .models import User, Clients, Comment
from .forms import ManagerSignUpForm, ExecutiveSignUpForm, LoginForm, ClientForm, CommentForm
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .decorators import manager_required,executive_required

class ManagerSignUpView(CreateView):
    model = User
    form_class = ManagerSignUpForm
    template_name = 'manger_signup.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'manager'
        return super().get_context_data(**kwargs)#additional data/context into the template determine maanger user type

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('manager-home') #save ,log and redirect the user
    
class ExecutiveSignUpView(CreateView):
    model = User
    form_class = ExecutiveSignUpForm
    template_name = 'executive_signup.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'executive'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('executive-home')
    
class LoginView(auth_views.LoginView):
    form_class = LoginForm
    template_name = 'login.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_manager:
                return reverse('manager-home')
            elif user.is_executive:
                return reverse('executive-home')
        else:
            return reverse('login')
        
@login_required
@manager_required
def manager_home(request):
    clients = Clients.objects.all() #fetching all the clients 
    context = {
        'clients': clients
        
    }
    return render(request, 'manager_home.html', context)

@login_required
@executive_required
def executive_home(request):
    clients = Clients.objects.filter(executive=request.user.executive)
    context = {
        'clients': clients
    }
    return render(request, 'executive_home.html', context)

# @login_required
# @manager_required #swapped
def create_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            clients = form.save(commit=False)
            # clients.manager = request.user.manager
            clients.save()
            return redirect('executive-home')
    else:
        form = ClientForm()
    return render(request, 'client.html', {'form': form})

@login_required
@executive_required #swapped
def create_comment(request, clients_id):
    clients = Clients.objects.get(id=clients_id)
    if Comment.objects.filter(client=clients, executive=request.user.executive).exists():
        return redirect('executive-home')
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comments = form.save(commit=False)
            comments.executive = request.user.execuitve
            comments.client = clients
            comments.save()
            return redirect('manager-home')
    else:
        form = CommentForm()
    return render(request, 'comment.html', {'form': form, 'client': clients})

@login_required
@manager_required
def manager_client_detail(request, clients_id):
    clients = Clients.objects.get(id=clients_id)
    if Comment.objects.filter(client=clients, manager=request.user.manager).exists():
        comments = Comment.objects.get(client=clients, manager=request.user.manager)
        commented = True
    else:
        comments = None
        commented = False
    context = {
        'client': clients,
        'comment': comments,
        'commented': commented
    }
    return render(request, 'manager_client_detail.html', context)

@login_required 
@executive_required
def executive_client_detail(request, clients_id):
    clients = Clients.objects.get(id=clients_id)
    if clients.executive != request.user.executive:
        return redirect('executive-home')
    comments = Comment.objects.filter(client=clients)
    context = {
        'client': clients,
        'comment': comments
    }
    return render(request, 'executive_client_detail.html', context)

@login_required
def view_user_permissions(request,user_id):
    user = User.objects.get(id=user_id)
    if user.is_manager:
        permissions = user.get_all_permissions()
        context = {
            'permissions':permissions
        }
        return render(request,'view_user_permissions.html',context)        
        
    elif user.is_executive:
        permissions = user.get_all_permissions()
        context = {
            'permissions': permissions
        }
        return render(request,'view_user_permissions.html',context)
    
# todo- admin view for creating user and creating and assigning permissions

