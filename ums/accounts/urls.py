from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("", views.manager_home, name="manager-home"),
    path("executive/", views.executive_home, name="executive-home"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("signup/manager/", views.ManagerSignUpView.as_view(), name="manager-signup"),
    path("signup/executive/", views.ExecutiveSignUpView.as_view(), name="executive-signup"),
    path('logout/', auth_views.LogoutView.as_view(template_name="users/logout.html"), name="logout"),
    path("manager/client/create/", views.create_client, name="create-client"),
    path("client/<int:clients_id>/comment/", views.create_comment, name="create-comment"),
    path("client/<int:clients_id>/", views.manager_client_detail, name="manager-client-detail"),
    path("executive/client/<int:clients_id>/", views.executive_client_detail, name="executive-client-detail"),
    # path("/<int:id>/permissions",views.view_user_permissions,name="user-permissions"),
]


#urls and template to be made for admin(crud) view user