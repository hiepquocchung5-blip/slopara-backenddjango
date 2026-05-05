from django.urls import path
from .views import (
    IslandListView, 
    IslandMachinesView, 
    MachineEnterView, 
    MachineLeaveView, 
    MachineHeartbeatView,
    SpinView, 
    SpinHistoryView, 
    HouseAnalyticsView
)

urlpatterns = [
    # Island & Floor Mapping
    path('islands/', IslandListView.as_view(), name='island_list'),
    path('islands/<int:island_id>/machines/', IslandMachinesView.as_view(), name='island_machines'),
    
    # Machine Occupancy (Live Multiplayer Concurrency)
    path('machines/<int:machine_id>/enter/', MachineEnterView.as_view(), name='machine_enter'),
    path('machines/<int:machine_id>/leave/', MachineLeaveView.as_view(), name='machine_leave'),
    path('machine/<int:machine_id>/heartbeat/', MachineHeartbeatView.as_view(), name='machine_heartbeat'),
    
    # Core Game Engine
    path('spin/', SpinView.as_view(), name='trigger_spin'),
    path('history/', SpinHistoryView.as_view(), name='spin_history'),
    
    # Admin Telemetry (Banker Portal)
    path('admin/analytics/', HouseAnalyticsView.as_view(), name='house_analytics'),
]