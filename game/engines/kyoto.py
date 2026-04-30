import random
from decimal import Decimal
from django.core.cache import cache
from django.db.models import Sum
from .base import BaseSlotEngine
from game.models import SpinHistory

class KyotoEngine(BaseSlotEngine):
    """
    Sector 01: Kyoto Zen (Island 100 V9.1 REAL HYBRID RTP70)
    Algorithm: Flag-First Lottery with Dynamic RTP-throttled GJP Probability.
    """
    SYMBOLS = ['GJP', 'LOGO', '7', 'Melon', 'Bell', 'Cherry', 'Replay']
    
    # 1. Exact Payouts mapped from simulation
    PAYOUTS = {
        'LOGO': Decimal('40.0'),  # Mapped from 💎
        '7': Decimal('15.0'),
        'Melon': Decimal('7.0'),
        'Bell': Decimal('3.0'),
        'Cherry': Decimal('2.0'),
        'Replay': Decimal('0.0')  # Replays trigger free spins
    }

    # 2. Exact Probabilities (Cumulative thresholds)
    # Replay(7%), Cherry(5.2%), Bell(3%), Melon(1.4%), 7(0.8%), LOGO(0.3%) -> Total Hit: ~17.7%
    PROB_THRESHOLDS = [
        (0.070, 'Replay'),
        (0.122, 'Cherry'),
        (0.152, 'Bell'),
        (0.166, 'Melon'),
        (0.174, '7'),
        (0.177, 'LOGO'),
    ]

    # 3. Hybrid GJP Constants
    BASE_JP_PROB = 0.00001
    ACCEL_FACTOR = 3
    TARGET_RTP = 0.67
    RTP_SOFT_RANGE = 0.03

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 1D array indices representing the 5 winning lines
        self.lines_indices = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8], # Horizontal
            [0, 4, 8], [2, 4, 6]             # Diagonal
        ]

    def _get_island_rtp(self):
        """
        Calculates the RTP of Kyoto Island. 
        Uses Redis/Local Memory caching for 60 seconds to prevent database 
        crashes during high-frequency concurrent spinning.
        """
        cache_key = f'island_{self.island.id}_rtp'
        rtp = cache.get(cache_key)
        
        if rtp is None:
            stats = SpinHistory.objects.filter(island_id=self.island.id).aggregate(
                w=Sum('win_amount'), b=Sum('bet_amount')
            )
            w = stats['w'] or Decimal('0')
            b = stats['b'] or Decimal('0')
            rtp = float(w / b) if b > 0 else 0.0
            
            cache.set(cache_key, rtp, 60)
            
        return rtp

    def calc_gjp_probability(self):
        """Dynamic Grand Jackpot formula translated directly from simulation."""
        gjp_val = float(self.pool.current_value)
        minimum_gjp = float(self.pool.hot_trigger)     # Maps to JS minimumGJP
        ceiling_gjp = float(self.pool.must_hit_value)  # Maps to JS ceilingGJP

        if gjp_val >= ceiling_gjp: return 1.0
        if gjp_val < minimum_gjp: return 0.0

        progress = (gjp_val - minimum_gjp) / (ceiling_gjp - minimum_gjp)
        progress = max(0.0, min(1.0, progress))

        prob = self.BASE_JP_PROB * (1 + progress * self.ACCEL_FACTOR)

        # Soft RTP Throttling
        island_rtp = self._get_island_rtp()
        if island_rtp > self.TARGET_RTP + self.RTP_SOFT_RANGE:
            prob *= 0.5
        elif island_rtp < self.TARGET_RTP - self.RTP_SOFT_RANGE:
            prob *= 1.3

        return prob

    def _has_accidental_win(self, flat_grid):
        """Prevents dead spins from accidentally aligning winning symbols."""
        for line in self.lines_indices:
            if flat_grid[line[0]] == flat_grid[line[1]] == flat_grid[line[2]]:
                return True
        return False

    def execute_spin(self):
        """
        Overrides BaseSlotEngine to use a Flag-First Lottery.
        The outcome is determined mathematically first, and the grid is built 
        to match the outcome (True Pachislot mechanic).
        """
        gjp_won = False
        win_amount = Decimal('0.0')
        lines_won = []
        free_spins_awarded = 0
        multiplier = 1
        result_symbol = None

        # 1. Roll for GJP
        jp_prob = self.calc_gjp_probability()
        if random.random() < jp_prob:
            result_symbol = 'GJP'
            gjp_won = True
        else:
            # 2. Roll for standard symbol payout
            r = random.random()
            for threshold, sym in self.PROB_THRESHOLDS:
                if r < threshold:
                    result_symbol = sym
                    break

        # 3. Construct the Matrix (1D array for easier index mapping)
        flat_grid = [random.choice(self.SYMBOLS) for _ in range(9)]
        
        if result_symbol:
            # Force the winning line
            chosen_line_idx = random.randint(0, 4)
            lines_won.append(chosen_line_idx)
            
            for pos in self.lines_indices[chosen_line_idx]:
                flat_grid[pos] = result_symbol

            if result_symbol == 'Replay':
                free_spins_awarded = 1
            elif result_symbol != 'GJP':
                win_amount = self.bet_amount * self.PAYOUTS[result_symbol]
        else:
            # Re-roll grid until there are strictly zero winning lines
            while self._has_accidental_win(flat_grid):
                flat_grid = [random.choice(self.SYMBOLS) for _ in range(9)]

        # 4. Convert flat grid back to 2D 3x3 matrix for frontend
        matrix = [
            flat_grid[0:3],
            flat_grid[3:6],
            flat_grid[6:9]
        ]

        return matrix, win_amount, gjp_won, lines_won, free_spins_awarded, multiplier

    def _force_jackpot_matrix(self):
        return [['GJP', 'GJP', 'GJP'], ['Cherry', 'Bell', 'Melon'], ['Melon', '7', 'LOGO']]