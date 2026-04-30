import random
from decimal import Decimal
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import GJP_Pool, SpinHistory, Machine, PlayerGameState
from users.models import User

# Fail-safe local engine in case 'engines' folder is missing/malformed
try:
    from .engines import get_engine
except ImportError:
    def get_engine(island_id):
        class FallbackEngine:
            def __init__(self, island, pool, bet_amount):
                self.island, self.pool, self.bet_amount = island, pool, bet_amount
            def execute_spin(self):
                SYMBOLS = ['GJP', 'LOGO', '7', 'Melon', 'Bell', 'Cherry', 'Replay']
                PAYOUTS = {'LOGO': Decimal('100.0'), '7': Decimal('50.0'), 'Melon': Decimal('20.0'), 'Bell': Decimal('10.0'), 'Cherry': Decimal('5.0'), 'Replay': Decimal('1.0')}
                weights = [0.01, 1, 3, 10, 20, 30, 35.99]
                
                force_gjp = self.pool.current_value >= self.pool.must_hit_value
                if force_gjp: weights = [100, 0, 0, 0, 0, 0, 0]
                
                matrix = [[random.choices(SYMBOLS, weights=weights)[0] for _ in range(3)] for _ in range(3)]
                win_amount, gjp_won, lines_won, free_spins, multiplier = Decimal('0.0'), False, [], 0, 1
                
                lines = [matrix[0], matrix[1], matrix[2], [matrix[0][0], matrix[1][1], matrix[2][2]], [matrix[0][2], matrix[1][1], matrix[2][0]]]
                for idx, line in enumerate(lines):
                    if line[0] == line[1] == line[2]:
                        sym = line[0]
                        if sym == 'GJP':
                            gjp_won, lines_won = True, lines_won + [idx]
                        elif sym in PAYOUTS:
                            win_amount += self.bet_amount * PAYOUTS[sym]
                            lines_won.append(idx)
                            if sym == '7': free_spins += 10
                
                if force_gjp and not gjp_won:
                    matrix = [['7', 'Melon', 'Cherry'], ['GJP', 'GJP', 'GJP'], ['Bell', 'Replay', 'LOGO']]
                    gjp_won, lines_won = True, lines_won + [1]
                    
                return matrix, win_amount, gjp_won, lines_won, free_spins, multiplier
        return FallbackEngine

@transaction.atomic
def process_spin(user_id, island_id, bet_amount, machine_id=None):
    bet_amount = Decimal(str(bet_amount))
    
    user = User.objects.select_for_update().get(id=user_id)
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

    EngineClass = get_engine(island_id)
    engine = EngineClass(island=pool.island, pool=pool, bet_amount=bet_amount)
    
    result = engine.execute_spin()
    if len(result) == 5:
        matrix, win_amount, gjp_won, lines_won, free_spins_awarded = result
        multiplier = 1
    else:
        matrix, win_amount, gjp_won, lines_won, free_spins_awarded, multiplier = result

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

    # CRITICAL FIX: Cast Decimals to Strings
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