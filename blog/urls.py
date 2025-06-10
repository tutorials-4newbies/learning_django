from django.urls import path
from . import views


app_name = "blog"

urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Existing URLs
    path('', views.index, name="index"),
    path('post/<int:post_id>/', views.single_post, name="single_post"),
    path('add_post/', views.add_post, name="add_post"),
    path('edit_post/<int:post_id>/', views.edit_post, name="edit_post"),
    path('edit_post_title/<int:post_id>/', views.edit_post_title, name="edit_post_title")
]