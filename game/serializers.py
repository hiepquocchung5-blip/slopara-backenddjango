from rest_framework import serializers
from decimal import Decimal
from .models import Island, GJP_Pool, SpinHistory, Machine

class GJPPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = GJP_Pool
        fields = ('current_value', 'must_hit_value', 'hot_trigger')

class IslandSerializer(serializers.ModelSerializer):
    gjp_pool = GJPPoolSerializer(read_only=True)
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Island
        fields = ('id', 'name', 'min_lifetime_deposit', 'total_machines', 'floors', 'gjp_pool', 'is_unlocked')

    def get_is_unlocked(self, obj):
        user = self.context['request'].user
        return user.lifetime_deposit >= obj.min_lifetime_deposit

class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = ('id', 'floor', 'machine_number', 'is_occupied')

class SpinRequestSerializer(serializers.Serializer):
    island_id = serializers.IntegerField()
    machine_id = serializers.IntegerField(required=False, allow_null=True) # FIXED: Accepts machine_id
    bet_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class SpinHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpinHistory
        fields = ('bet_amount', 'win_amount', 'symbols_matrix', 'lines_won', 'is_gjp_win', 'timestamp')