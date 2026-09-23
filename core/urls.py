"""
URL configuration for core project.

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
from django.urls import path
from django.views.generic import RedirectView
from api.views import CombinedTelemetryView, MQTTControlView

urlpatterns = [
    # Django administration panel
    path('admin/', admin.site.urls),
    
    # Redirect the root URL ('/') directly to our telemetry API
    path('', RedirectView.as_view(url='/api/control/mqtt/', permanent=False)),
    
    # Single endpoint for all IoT telemetry data
    path('api/telemetry/', CombinedTelemetryView.as_view(), name='all_telemetry'),
    
    # New endpoint for sending control commands
    path('api/control/mqtt/', MQTTControlView.as_view(), name='control_mqtt'),
]

