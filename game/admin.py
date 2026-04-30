from django.contrib import admin
from django.db.models import Sum
from .models import Island, GJP_Pool, Machine, SpinHistory

class GJPPoolInline(admin.StackedInline):
    model = GJP_Pool
    can_delete = False

@admin.register(Island)
class IslandAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_lifetime_deposit', 'total_machines', 'get_gjp_value')
    inlines = [GJPPoolInline]

    def get_gjp_value(self, obj):
        return obj.gjp_pool.current_value if hasattr(obj, 'gjp_pool') else 'N/A'
    get_gjp_value.short_description = 'Current GJP'

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('island', 'floor', 'machine_number', 'is_occupied', 'current_player')
    list_filter = ('island', 'is_occupied', 'floor')
    search_fields = ('machine_number', 'current_player__phone_number')

@admin.register(SpinHistory)
class SpinHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'island', 'bet_amount', 'win_amount', 'is_gjp_win', 'timestamp')
    list_filter = ('is_gjp_win', 'island', 'timestamp')
    search_fields = ('user__phone_number',)
    readonly_fields = ('timestamp',)
    
    # Calculate RTP for the selected records
    def get_changelist_instance(self, request):
        cl = super().get_changelist_instance(request)
        queryset = cl.queryset
        
        total_bet = queryset.aggregate(Sum('bet_amount'))['bet_amount__sum'] or 0
        total_win = queryset.aggregate(Sum('win_amount'))['win_amount__sum'] or 0
        rtp = (total_win / total_bet * 100) if total_bet > 0 else 0
        
        self.message_user(request, f"Filtered Records RTP: {rtp:.2f}% | Profit: {total_bet - total_win} MMK")
        return cl