from django.urls import path
from .views import (
    IslandListView, 
    IslandMachinesView, 
    MachineEnterView, 
    MachineLeaveView, 
    SpinView, 
    SpinHistoryView, 
    HouseAnalyticsView
)

urlpatterns = [
    # Island & Floor Mapping
    path('islands/', IslandListView.as_view(), name='island_list'),
    path('islands/<int:island_id>/machines/', IslandMachinesView.as_view(), name='island_machines'),
    
    # Machine Occupancy (Live Multiplayer)
    path('machines/<int:machine_id>/enter/', MachineEnterView.as_view(), name='machine_enter'),
    path('machines/<int:machine_id>/leave/', MachineLeaveView.as_view(), name='machine_leave'),
    
    # Core Game Loop
    path('spin/', SpinView.as_view(), name='trigger_spin'),
    path('history/', SpinHistoryView.as_view(), name='spin_history'),
    
    # Admin Telemetry
    path('admin/analytics/', HouseAnalyticsView.as_view(), name='house_analytics'),
]