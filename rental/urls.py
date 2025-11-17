from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('booking/', views.booking_page, name='booking_page'),
    path('manage-buildings/', views.manage_buildings, name='manage_buildings'),
    path('api/room/<int:room_id>/update/', views.update_room, name='update_room'),
    path('api/room/add/', views.add_room, name='add_room'),
    path('api/room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
]
