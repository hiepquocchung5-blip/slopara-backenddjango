from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction, OperationalError
from django.db.models import Sum, Count
from decimal import Decimal
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import traceback
import inspect
import time

from .models import Island, Machine, SpinHistory
from .serializers import IslandSerializer, MachineSerializer, SpinRequestSerializer, SpinHistorySerializer
from .utils import process_spin
from rest_framework.throttling import UserRateThrottle

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
        return Machine.objects.filter(island_id=self.kwargs['island_id'], floor=self.request.query_params.get('floor', 1)).order_by('machine_number')

class MachineEnterView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, machine_id):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Removed select_for_update() which breaks SQLite transaction states
                    machine = Machine.objects.get(id=machine_id)
                    
                    if machine.is_occupied and machine.current_player != request.user:
                        return Response({"error": "Machine is currently occupied."}, status=status.HTTP_409_CONFLICT)
                    
                    machine.is_occupied = True
                    machine.current_player = request.user
                    machine.save()

                # Broadcast outside of atomic block to free the DB lock faster
                try:
                    channel_layer = get_channel_layer()
                    if channel_layer:
                        async_to_sync(channel_layer.group_send)(
                            'global_casino_floor', {'type': 'machine_update', 'machine_id': machine.id, 'is_occupied': True}
                        )
                except Exception: pass
                
                return Response({"status": "Success", "machine_id": machine.id})
                
            except OperationalError as e:
                # Handle SQLite "database is locked" gracefully
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                traceback.print_exc()
                return Response({"error": "Database busy. Please try again."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Machine.DoesNotExist:
                return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                traceback.print_exc()
                return Response({"error": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MachineLeaveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, machine_id):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    machine = Machine.objects.get(id=machine_id)
                        
                    if machine.current_player == request.user:
                        machine.is_occupied = False
                        machine.current_player = None
                        machine.save()

                try:
                    channel_layer = get_channel_layer()
                    if channel_layer:
                        async_to_sync(channel_layer.group_send)(
                            'global_casino_floor', {'type': 'machine_update', 'machine_id': machine.id, 'is_occupied': False}
                        )
                except Exception: pass
                    
                return Response({"status": "Success"})
                
            except OperationalError as e:
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                traceback.print_exc()
                return Response({"error": "Database busy. Please try again."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Machine.DoesNotExist:
                return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                traceback.print_exc()
                return Response({"error": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SpinView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SpinRateThrottle]
    
    def post(self, request):
        serializer = SpinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 1. Dynamic argument injection
                sig = inspect.signature(process_spin)
                kwargs = {
                    'user_id': request.user.id,
                    'island_id': serializer.validated_data['island_id'],
                    'bet_amount': serializer.validated_data['bet_amount']
                }
                
                if 'machine_id' in sig.parameters:
                    kwargs['machine_id'] = serializer.validated_data.get('machine_id')

                # 2. Execute
                result = process_spin(**kwargs)
                
                # 3. Final Serialization Fail-Safe
                if isinstance(result.get('win_amount'), Decimal): result['win_amount'] = str(result['win_amount'])
                if isinstance(result.get('new_balance'), Decimal): result['new_balance'] = str(result['new_balance'])
                if isinstance(result.get('gjp_current_value'), Decimal): result['gjp_current_value'] = str(result['gjp_current_value'])
                
                if 'free_spins_remaining' not in result: result['free_spins_remaining'] = 0
                if 'multiplier' not in result: result['multiplier'] = 1

                return Response(result, status=status.HTTP_200_OK)
                
            except OperationalError as e:
                # Retries spin transaction if SQLite locks during pool updates
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                traceback.print_exc()
                return Response({"error": "Database busy. Please try again."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except ValueError as e: 
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e: 
                traceback.print_exc()
                return Response({"error": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SpinHistoryView(generics.ListAPIView):
    serializer_class = SpinHistorySerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return SpinHistory.objects.filter(user=self.request.user)[:50]

class HouseAnalyticsView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        stats = SpinHistory.objects.aggregate(total_spins=Count('id'), total_wagered=Sum('bet_amount'), total_paid_out=Sum('win_amount'))
        wagered, paid_out = stats['total_wagered'] or Decimal('0.00'), stats['total_paid_out'] or Decimal('0.00')
        return Response({
            "total_spins": stats['total_spins'],
            "total_wagered": str(wagered), "total_paid_out": str(paid_out),
            "house_profit": str(wagered - paid_out), "rtp_percentage": round(float((paid_out / wagered * 100) if wagered > 0 else Decimal('0.00')), 2)
        })