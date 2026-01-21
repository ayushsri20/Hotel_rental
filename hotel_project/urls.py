"""
URL configuration for hotel_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rental import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manage-buildings/', views.manage_buildings, name='manage_buildings'),
    path('manage-guests/', views.manage_guests, name='manage_guests'),
    path('api/room/<int:room_id>/update/', views.update_room, name='update_room'),
    path('api/room/add/', views.add_room, name='add_room'),
    path('api/room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('api/guest/add/', views.add_guest, name='add_guest'),
    path('api/guest/<int:guest_id>/update/', views.update_guest, name='update_guest'),
    path('api/guest/<int:guest_id>/delete/', views.delete_guest, name='delete_guest'),
    path('api/guests/', views.get_guests, name='get_guests'),
    path('manage-payments/', views.manage_payments, name='manage_payments'),
    path('manage-electricity-bills/', views.manage_electricity_bills, name='manage_electricity_bills'),
    path('api/payment/create/', views.create_monthly_payment, name='create_monthly_payment'),
    path('api/payment/record/', views.record_payment, name='record_payment'),
    path('api/bill/create/', views.create_electricity_bill, name='create_electricity_bill'),
    path('api/bill/record/', views.record_electricity_payment, name='record_electricity_payment'),
    path('api/payment-history/<int:room_id>/', views.get_payment_history, name='get_payment_history'),
    path('api/bill-history/<int:room_id>/', views.get_electricity_history, name='get_electricity_history'),
    
    # Booking Management
    path('booking/', views.booking_page, name='booking_page'),
    path('api/available-rooms/', views.get_available_rooms, name='get_available_rooms'),
    path('api/booking/submit/', views.submit_booking, name='submit_booking'),
    path('api/room/<int:room_id>/tenants/', views.get_room_tenants, name='get_room_tenants'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Include app-level URL patterns (ensures names like 'performance_dashboard' are resolvable)
from django.urls import include
urlpatterns += [
    path('', include('rental.urls')),
]
