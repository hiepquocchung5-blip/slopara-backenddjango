from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import traceback

from .models import Island, Machine, SpinHistory, PlayerGameState
from .serializers import IslandSerializer, MachineSerializer, SpinRequestSerializer, SpinHistorySerializer, PlayerGameStateSerializer
from .utils import process_spin
from rest_framework.throttling import UserRateThrottle

# Anti-Cheat Throttle: Prevents auto-clicker scripts from bankrupting the pool or crashing the DB
class SpinRateThrottle(UserRateThrottle):
    scope = 'spin'
    rate = '1/second'

class IslandListView(generics.ListAPIView):
    queryset = Island.objects.all().order_by('min_lifetime_deposit')
    serializer_class = IslandSerializer
    permission_classes = [IsAuthenticated]

class IslandMachinesView(generics.ListAPIView):
    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Machine.objects.filter(
            island_id=self.kwargs['island_id'], 
            floor=self.request.query_params.get('floor', 1)
        ).order_by('machine_number')


class MachineEnterView(APIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, machine_id):
        try:
            # PostgreSQL Native Lock: Prevents two users from taking the same machine
            machine = Machine.objects.select_for_update().get(id=machine_id)
            
            if machine.is_occupied and machine.current_player != request.user:
                return Response({"error": "Machine is currently occupied."}, status=status.HTTP_409_CONFLICT)
            
            machine.is_occupied = True
            machine.current_player = request.user
            machine.last_ping = timezone.now()
            machine.save()

            # Retrieve any active game state (e.g., disconnected during Free Spins)
            state, _ = PlayerGameState.objects.get_or_create(user=request.user, island_id=machine.island_id)
            state_data = PlayerGameStateSerializer(state).data

            # Broadcast occupancy to the hall
            try:
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        'global_casino_floor', {'type': 'machine_update', 'machine_id': machine.id, 'is_occupied': True}
                    )
            except Exception: pass
            
            return Response({
                "status": "Success", 
                "machine_id": machine.id,
                "active_state": state_data
            })
            
        except Machine.DoesNotExist:
            return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MachineLeaveView(APIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, machine_id):
        try:
            machine = Machine.objects.select_for_update().get(id=machine_id)
                
            if machine.current_player == request.user:
                machine.is_occupied = False
                machine.current_player = None
                machine.last_ping = None
                machine.save()

                try:
                    channel_layer = get_channel_layer()
                    if channel_layer:
                        async_to_sync(channel_layer.group_send)(
                            'global_casino_floor', {'type': 'machine_update', 'machine_id': machine.id, 'is_occupied': False}
                        )
                except Exception: pass
                    
            return Response({"status": "Success"})
            
        except Machine.DoesNotExist:
            return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MachineHeartbeatView(APIView):
    """Maintains the machine lock. Called every 30 seconds by the frontend."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, machine_id):
        try:
            machine = Machine.objects.select_for_update().get(id=machine_id, current_player=request.user)
            machine.last_ping = timezone.now()
            machine.save(update_fields=['last_ping'])
            return Response({"status": "alive"})
        except Machine.DoesNotExist:
            return Response({"error": "Ownership revoked or machine expired."}, status=status.HTTP_403_FORBIDDEN)


class SpinView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SpinRateThrottle]
    
    def post(self, request):
        serializer = SpinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Passes to the Transactional Engine in utils.py
            result = process_spin(
                user_id=request.user.id,
                island_id=serializer.validated_data['island_id'],
                bet_amount=serializer.validated_data['bet_amount'],
                machine_id=serializer.validated_data.get('machine_id')
            )
            
            # Final Serialization Fail-Safe: Ensures JSON encoding doesn't break on Decimals
            if isinstance(result.get('win_amount'), Decimal): result['win_amount'] = str(result['win_amount'])
            if isinstance(result.get('new_balance'), Decimal): result['new_balance'] = str(result['new_balance'])
            if isinstance(result.get('gjp_current_value'), Decimal): result['gjp_current_value'] = str(result['gjp_current_value'])
            
            if 'free_spins_remaining' not in result: result['free_spins_remaining'] = 0
            if 'multiplier' not in result: result['multiplier'] = 1

            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e: 
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e: 
            traceback.print_exc()
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SpinHistoryView(generics.ListAPIView):
    serializer_class = SpinHistorySerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return SpinHistory.objects.filter(user=self.request.user)[:50]


class HouseAnalyticsView(APIView):
    """Admin endpoint for the Banker Portal to monitor floor performance."""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        stats = SpinHistory.objects.aggregate(
            total_spins=Count('id'), 
            total_wagered=Sum('bet_amount'), 
            total_paid_out=Sum('win_amount')
        )
        wagered = stats['total_wagered'] or Decimal('0.00')
        paid_out = stats['total_paid_out'] or Decimal('0.00')
        rtp = float((paid_out / wagered * 100) if wagered > 0 else Decimal('0.00'))
        
        return Response({
            "total_spins": stats['total_spins'],
            "total_wagered": str(wagered), 
            "total_paid_out": str(paid_out),
            "house_profit": str(wagered - paid_out), 
            "rtp_percentage": round(rtp, 2)
        })