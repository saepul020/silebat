from django.urls import path
from .views import display, display_active_data, export_chart, index

app_name = 'dashboard'

urlpatterns = [
    path('', index, name='index'),
    path('export-chart/', export_chart, name='export_chart'),
    path('display/<slug:portal_slug>/active-data/', display_active_data, name='display_active_data'),
    path('display/<slug:portal_slug>/', display, name='display'),
]
