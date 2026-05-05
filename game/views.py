import logging
from decimal import Decimal

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.throttling import UserRateThrottle
from rest_framework.pagination import PageNumberPagination

from django.db import transaction, OperationalError
from django.db.models import Sum, Count, F
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Island, Machine, SpinHistory
from .serializers import IslandSerializer, MachineSerializer, SpinRequestSerializer, SpinHistorySerializer
from .utils import process_spin

logger = logging.getLogger(__name__)

class SpinRateThrottle(UserRateThrottle):
    scope = 'spin'
    rate = '3/second' # Increased slightly to allow fast physical taps, DB locks will handle the rest

# ==============================================================================
# CASINO FLOOR & MACHINE MANAGEMENT
# ==============================================================================
class IslandListView(generics.ListAPIView):
    queryset = Island.objects.select_related('gjp_pool').all().order_by('min_lifetime_deposit')
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

class ActiveSessionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        machine = Machine.objects.filter(current_player=request.user).first()
        if machine:
            return Response({
                "active_machine": machine.id, 
                "island_id": machine.island_id,
                "machine_number": machine.machine_number
            })
        return Response({"active_machine": None})

class MachineEnterView(APIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, machine_id):
        try:
            machine = Machine.objects.select_for_update(nowait=True).get(id=machine_id)
            now = timezone.now()

            if machine.is_occupied and machine.current_player != request.user:
                if machine.last_ping and (now - machine.last_ping).total_seconds() > 60:
                    logger.info(f"Evicting ghost user {machine.current_player_id} from Machine {machine.id}")
                else:
                    return Response({"error": "Machine is currently occupied."}, status=status.HTTP_409_CONFLICT)
            
            Machine.objects.filter(current_player=request.user).update(
                is_occupied=False, current_player=None, last_ping=None
            )

            machine.is_occupied = True
            machine.current_player = request.user
            machine.last_ping = now
            machine.save()

            async_to_sync(get_channel_layer().group_send)(
                'global_casino_floor', 
                {'type': 'machine_update', 'machine_id': machine.id, 'is_occupied': True}
            )
            return Response({"status": "Success", "machine_id": machine.id})
            
        except OperationalError:
            return Response({"error": "Machine is currently being accessed. Try again."}, status=status.HTTP_409_CONFLICT)
        except Machine.DoesNotExist:
            return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)

class MachineLeaveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, machine_id):
        # Direct atomic UPDATE avoids select_for_update deadlocks
        updated = Machine.objects.filter(id=machine_id, current_player=request.user).update(
            is_occupied=False, current_player=None, last_ping=None
        )
        
        if updated:
            async_to_sync(get_channel_layer().group_send)(
                'global_casino_floor', 
                {'type': 'machine_update', 'machine_id': machine_id, 'is_occupied': False}
            )
            return Response({"status": "Success"})
        return Response({"error": "Machine not found or not owned by you."}, status=status.HTTP_404_NOT_FOUND)

class MachineHeartbeatView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, machine_id):
        # High-performance atomic update. Bypasses Python memory and row locks entirely.
        updated = Machine.objects.filter(id=machine_id, current_player=request.user).update(last_ping=timezone.now())
        if updated:
            return Response({"status": "alive", "ttl": 60})
        return Response({"error": "Ownership revoked or machine expired."}, status=status.HTTP_403_FORBIDDEN)

# ==============================================================================
# CORE GAME ENGINE ROUTING
# ==============================================================================
class SpinView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SpinRateThrottle]
    
    def post(self, request):
        serializer = SpinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        island_id = serializer.validated_data['island_id']
        bet_amount = serializer.validated_data['bet_amount']
        machine_id = serializer.validated_data.get('machine_id')

        if machine_id:
            # High-performance verification and ping update in a single SQL query
            updated = Machine.objects.filter(id=machine_id, current_player=request.user).update(last_ping=timezone.now())
            if not updated:
                return Response({"error": "You do not have a lock on this machine."}, status=status.HTTP_403_FORBIDDEN)

        try:
            result = process_spin(
                user_id=request.user.id, 
                island_id=island_id, 
                bet_amount=bet_amount,
                machine_id=machine_id
            )
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e: 
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except OperationalError as e:
            # CRITICAL FIX: Catch DB Locks (Concurrent Spin Taps) and reject gracefully
            logger.warning(f"DB Lock Contention [User {request.user.id}]: {str(e)}")
            return Response({"error": "Processing previous spin. Please wait a moment."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e: 
            logger.error(f"Engine Crash [User {request.user.id}]: {str(e)}", exc_info=True)
            return Response({"error": f"Math Engine Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class SpinHistoryView(generics.ListAPIView):
    serializer_class = SpinHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self): 
        return SpinHistory.objects.filter(user=self.request.user).select_related('island').order_by('-timestamp')

# ==============================================================================
# TELEMETRY & ANALYTICS (BANKER PORTAL)
# ==============================================================================
class HouseAnalyticsView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        global_stats = SpinHistory.objects.aggregate(
            total_spins=Count('id'), 
            total_wagered=Sum('bet_amount'), 
            total_paid_out=Sum('win_amount')
        )
        
        g_wagered = global_stats['total_wagered'] or Decimal('0.00')
        g_paid_out = global_stats['total_paid_out'] or Decimal('0.00')
        g_rtp = float((g_paid_out / g_wagered * 100) if g_wagered > 0 else Decimal('0.00'))

        island_stats = list(SpinHistory.objects.values(
            island_name=F('island__name')
        ).annotate(
            spins=Count('id'),
            wagered=Sum('bet_amount'),
            paid=Sum('win_amount')
        ).order_by('island_name'))

        for stat in island_stats:
            w = stat['wagered'] or Decimal('0.00')
            p = stat['paid'] or Decimal('0.00')
            stat['rtp'] = round(float((p / w * 100) if w > 0 else 0), 2)
            stat['profit'] = str(w - p)
            stat['wagered'] = str(w)
            stat['paid'] = str(p)

        return Response({
            "global": {
                "total_spins": global_stats['total_spins'],
                "total_wagered": str(g_wagered), 
                "total_paid_out": str(g_paid_out),
                "house_profit": str(g_wagered - g_paid_out), 
                "rtp_percentage": round(g_rtp, 2)
            },
            "sectors": island_stats
        })