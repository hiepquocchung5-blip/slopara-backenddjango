import random
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import GJP_Pool, SpinHistory, Machine, PlayerGameState
from users.models import User

# ==============================================================================
# FALLBACK ENGINE (V9.2 Architecture)
# Operates if the `engines` module fails to load, preventing complete downtime.
# ==============================================================================
try:
    from .engines import get_engine
except ImportError:
    def get_engine(island_id):
        class FallbackEngine:
            SYMBOLS = ['GJP', 'LOGO', '7', 'Melon', 'Bell', 'Cherry', 'Replay']
            PAYOUTS = {
                'LOGO': Decimal('25.0'), '7': Decimal('10.0'), 'Melon': Decimal('5.0'), 
                'Bell': Decimal('3.0'), 'Cherry': Decimal('2.0'), 'Replay': Decimal('0.0')
            }
            # V9.2 Cumulative Probabilities (31.2% Hit Rate)
            PROB_THRESHOLDS = [
                (0.150, 'Replay'), (0.225, 'Cherry'), (0.280, 'Bell'),
                (0.302, 'Melon'), (0.310, '7'), (0.312, 'LOGO')
            ]
            LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 4, 8], [2, 4, 6]]

            def __init__(self, island, pool, bet_amount):
                self.island = island
                self.pool = pool
                self.bet_amount = Decimal(str(bet_amount))

            def _has_accidental_win(self, flat_grid):
                """Scans to ensure dead spins don't accidentally align."""
                for line in self.LINES:
                    if flat_grid[line[0]] == flat_grid[line[1]] == flat_grid[line[2]]:
                        return True
                return False

            def execute_spin(self):
                gjp_won = False
                win_amount = Decimal('0.0')
                free_spins = 0
                multiplier = 1
                result_sym = None
                lines_won = []

                # 1. GJP Roll (Simplified for fallback stability)
                gjp_val = float(self.pool.current_value)
                min_gjp = float(self.pool.hot_trigger)
                ceil_gjp = float(self.pool.must_hit_value)
                
                if gjp_val >= ceil_gjp:
                    gjp_won = True
                    result_sym = 'GJP'
                else:
                    progress = max(0.0, min(1.0, (gjp_val - min_gjp) / (ceil_gjp - min_gjp) if ceil_gjp > min_gjp else 0))
                    prob = 0.00001 * (1 + progress * 3)
                    if random.random() < prob:
                        gjp_won = True
                        result_sym = 'GJP'
                    else:
                        # 2. Base Game Roll
                        r = random.random()
                        for thresh, sym in self.PROB_THRESHOLDS:
                            if r < thresh:
                                result_sym = sym
                                break

                # 3. Payout Calculation
                if result_sym == 'Replay':
                    free_spins = 1
                elif result_sym and result_sym != 'GJP':
                    win_amount = self.bet_amount * self.PAYOUTS[result_sym]

                # 4. Grid Generation
                flat_grid = [random.choice(self.SYMBOLS) for _ in range(9)]
                if result_sym:
                    chosen_line = random.randint(0, 4)
                    lines_won.append(chosen_line)
                    for pos in self.LINES[chosen_line]:
                        flat_grid[pos] = result_sym
                else:
                    while self._has_accidental_win(flat_grid):
                        flat_grid = [random.choice(self.SYMBOLS) for _ in range(9)]

                matrix = [flat_grid[0:3], flat_grid[3:6], flat_grid[6:9]]
                
                return matrix, win_amount, gjp_won, lines_won, free_spins, multiplier
        return FallbackEngine


# ==============================================================================
# TRANSACTIONAL SPIN PROCESSOR
# ==============================================================================
@transaction.atomic
def process_spin(user_id, island_id, bet_amount, machine_id=None):
    bet_amount = Decimal(str(bet_amount))
    
    # We select_related to access the referrer's user_type without hitting the DB twice
    user = User.objects.select_related('referred_by').select_for_update().get(id=user_id)
    pool = GJP_Pool.objects.select_for_update().get(island_id=island_id)
    
    try:
        game_state, _ = PlayerGameState.objects.select_for_update().get_or_create(user=user, island_id=island_id)
        is_free_spin = game_state.free_spins_remaining > 0
    except ImportError:
        is_free_spin = False
        game_state = None

    if is_free_spin and game_state:
        bet_amount = game_state.locked_bet_amount
    else:
        if user.balance < bet_amount:
            raise ValueError("Insufficient balance")
        
        user.balance -= bet_amount
        pool.current_value += (bet_amount * pool.contribution_rate)

        # =========================================================================
        # CFO ENGINE: DISTRIBUTE REFERRAL COMMISSIONS (ONLY ON PAID BASE SPINS)
        # =========================================================================
        if user.referred_by_id:
            base_commission_pool = bet_amount * Decimal('0.01') # 1% Base Pool
            commission_rate = user.referred_by.get_commission_rate()
            
            if commission_rate > 0:
                final_commission = base_commission_pool * commission_rate
                
                # CRITICAL ENGINEERING: Lock-free F() expression prevents DB deadlocks
                User.objects.filter(id=user.referred_by_id).update(
                    commission_balance=F('commission_balance') + final_commission,
                    total_commission_earned=F('total_commission_earned') + final_commission
                )
        # =========================================================================

    EngineClass = get_engine(island_id)
    engine = EngineClass(island=pool.island, pool=pool, bet_amount=bet_amount)
    
    # Handle both old 5-return engines and new 6-return engines safely
    result = engine.execute_spin()
    if len(result) == 5:
        matrix, win_amount, gjp_won, lines_won, free_spins_awarded = result
        multiplier = 1
    else:
        matrix, win_amount, gjp_won, lines_won, free_spins_awarded, multiplier = result

    # State processing
    if game_state:
        if is_free_spin:
            game_state.free_spins_remaining -= 1
            if game_state.free_spins_remaining <= 0:
                game_state.free_spins_remaining = 0
                game_state.locked_bet_amount = Decimal('0.00')

        if free_spins_awarded > 0:
            game_state.free_spins_remaining += free_spins_awarded
            game_state.locked_bet_amount = bet_amount
        game_state.save()

    # Jackpot logic
    if gjp_won:
        jackpot_amount = pool.current_value
        win_amount += jackpot_amount
        pool.current_value = pool.base_seed 
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)('global_casino_floor', {
                'type': 'global_jackpot_hit', 'island_id': island_id, 'island_name': pool.island.name,
                'winner_name': user.username or user.phone_number, 'amount': str(jackpot_amount)
            })
        except Exception: pass

    user.balance += win_amount
    user.save()
    pool.save()

    machine_obj = None
    if machine_id:
        try:
            machine_obj = Machine.objects.get(id=machine_id)
        except Machine.DoesNotExist:
            pass

    SpinHistory.objects.create(
        user=user, island_id=island_id, machine=machine_obj,
        bet_amount=bet_amount, win_amount=win_amount,
        symbols_matrix=matrix, lines_won=lines_won, is_gjp_win=gjp_won
    )

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)('global_casino_floor', {
            'type': 'gjp_update', 'island_id': island_id, 'new_value': str(pool.current_value)
        })
    except Exception: pass

    return {
        'matrix': matrix,
        'win_amount': str(win_amount),
        'lines_won': lines_won,
        'is_gjp_win': gjp_won,
        'new_balance': str(user.balance),
        'gjp_current_value': str(pool.current_value),
        'free_spins_remaining': game_state.free_spins_remaining if game_state else 0,
        'multiplier': multiplier
    }