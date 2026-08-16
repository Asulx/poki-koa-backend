from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Aquí conectamos nuestra API. Todas las rutas empezarán con /api/
    path('api/', include('cunas.urls')), 
]