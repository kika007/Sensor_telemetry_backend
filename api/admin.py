from django.contrib import admin
from .models import SensorDevice

@admin.register(SensorDevice)
class SensorDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'data_topic', 'is_active')
    list_filter = ('is_active', 'location')
    search_fields = ('name', 'location')
