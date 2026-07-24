from .import views
from django.urls import path


urlpatterns = [
    path("",views.home, name="home"),
    path("lgin/",views.login_view, name="login"),
    path("register/",views.register_view, name="register-user"),
    path("logout/",views.logout_view, name="logout"),

]