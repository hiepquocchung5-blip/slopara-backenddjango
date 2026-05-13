import random
from decimal import Decimal
from typing import List, Tuple, Optional
from django.core.cache import cache
from django.db.models import Sum
from .base import BaseSlotEngine
from game.models import SpinHistory

class KyotoEngine(BaseSlotEngine):
    """
    Sector 01: Kyoto Zen (Island 100 V10.1 REAL HYBRID RTP70)
    Architecture: Dual-State Hybrid Lottery (Cold/Hot RTP) with Strict Visual Grid.
    V10.1 Updates: 
    - Implemented HTML/JS Simulator probabilities.
    - 2 Distinct RTP phases to build hype:
      * COLD (Before Hot Trigger): ~69% Base RTP
      * HOT (After Hot Trigger): ~85% Base RTP (Higher hits, keeps player engaged)
    """
    SYMBOLS = ['GJP', 'LOGO', '7', 'Melon', 'Bell', 'Cherry', 'Replay']
    
    # Exact Payouts mapped from V10.1 JS Simulation
    PAYOUTS = {
        'LOGO': Decimal('25.0'),   # JS: 💎
        '7': Decimal('10.0'),      # JS: 7️⃣
        'Melon': Decimal('5.0'),   # JS: 🍉
        'Bell': Decimal('3.0'),    # JS: 🔔
        'Cherry': Decimal('2.0'),  # JS: 🍒
        'Replay': Decimal('0.0')   # JS: 🔄 (Triggers Free Spin)
    }

    # STATE 1: COLD PLAY (Exact JS Probabilities: ~69% Base RTP)
    COLD_PROB_THRESHOLDS = [
        (0.140, 'Replay'),  # 14.0%
        (0.200, 'Cherry'),  # 6.0%
        (0.230, 'Bell'),    # 3.0%
        (0.246, 'Melon'),   # 1.6%
        (0.261, '7'),       # 1.5%
        (0.271, 'LOGO'),    # 1.0%
    ]

    # STATE 2: HOT PLAY (Triggered when Pool >= Hot Trigger: ~85% Base RTP)
    # Increases hit frequency so players feel the machine "heating up"
    HOT_PROB_THRESHOLDS = [
        (0.160, 'Replay'),  # 16.0% (More Free Spins)
        (0.240, 'Cherry'),  # 8.0%
        (0.280, 'Bell'),    # 4.0%
        (0.300, 'Melon'),   # 2.0%
        (0.320, '7'),       # 2.0%
        (0.335, 'LOGO'),    # 1.5%
    ]

    # Hybrid GJP Constants (From V10.1 JS Simulator)
    BASE_JP_PROB = 0.00001
    ACCEL_FACTOR = 3
    TARGET_RTP = 0.67
    RTP_SOFT_RANGE = 0.03

    # CRITICAL FIX: All possible 3-in-a-row visual combinations
    ALL_LINES = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # Horizontal (Valid Paylines)
        [0, 4, 8], [2, 4, 6],            # Diagonal (Valid Paylines)
        [0, 3, 6], [1, 4, 7], [2, 5, 8]  # Vertical (Visual Only - Strictly Prevented)
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lines_indices = self.ALL_LINES[:5] # The 5 actual paying lines

    # --- CORE MATH & CACHING ---

    def _get_island_rtp(self) -> float:
        """Fetches Island RTP from Redis/Memory cache (60s TTL) to prevent DB locks."""
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

    def _roll_gjp(self) -> bool:
        """Calculates and rolls the dynamic Grand Jackpot probability."""
        gjp_val = float(self.pool.current_value)
        minimum_gjp = float(self.pool.hot_trigger)
        ceiling_gjp = float(self.pool.must_hit_value)

        # Force hit if ceiling reached, mathematically block if below hot trigger
        if gjp_val >= ceiling_gjp: return True
        if gjp_val < minimum_gjp: return False

        progress = max(0.0, min(1.0, (gjp_val - minimum_gjp) / (ceiling_gjp - minimum_gjp)))
        prob = self.BASE_JP_PROB * (1 + progress * self.ACCEL_FACTOR)

        # Soft RTP Throttling (Dynamic Correction)
        island_rtp = self._get_island_rtp()
        if island_rtp > self.TARGET_RTP + self.RTP_SOFT_RANGE:
            prob *= 0.5
        elif island_rtp < self.TARGET_RTP - self.RTP_SOFT_RANGE:
            prob *= 1.3

        return random.random() < prob

    def _roll_base_game(self, is_hot: bool) -> Optional[str]:
        """Rolls the standard RNG using dynamic thresholds based on the GJP Pool State."""
        r = random.random()
        
        # Determine which RTP state table to use
        thresholds = self.HOT_PROB_THRESHOLDS if is_hot else self.COLD_PROB_THRESHOLDS
        
        for threshold, sym in thresholds:
            if r < threshold:
                return sym
        return None

    # --- STRICT GRID GENERATION ---

    def _has_visual_conflict(self, flat_grid: List[str], allowed_line_idx: int = -1) -> bool:
        """
        Scans all 8 possible straight lines (Horizontal, Diagonal, Vertical).
        If 3 symbols match anywhere EXCEPT the intentionally forced payline, 
        it is flagged as a conflict and rejected to protect player trust.
        """
        for idx, line in enumerate(self.ALL_LINES):
            if idx == allowed_line_idx:
                continue 
                
            if flat_grid[line[0]] == flat_grid[line[1]] == flat_grid[line[2]]:
                return True 
                
        return False

    def _generate_grid(self, winning_symbol: Optional[str]) -> Tuple[List[List[str]], List[int]]:
        """Constructs a visual 3x3 matrix that mathematically matches the outcome."""
        lines_won = []

        if winning_symbol:
            chosen_line_idx = random.randint(0, 4)
            lines_won.append(chosen_line_idx)
            
            while True:
                flat_grid = [random.choice(self.SYMBOLS) for _ in range(9)]
                
                for pos in self.lines_indices[chosen_line_idx]:
                    flat_grid[pos] = winning_symbol
                    
                if not self._has_visual_conflict(flat_grid, allowed_line_idx=chosen_line_idx):
                    break
        else:
            # Dead Spin: Verify ABSOLUTELY NO 3-in-a-row matches exist anywhere
            while True:
                flat_grid = [random.choice(self.SYMBOLS) for _ in range(9)]
                if not self._has_visual_conflict(flat_grid, allowed_line_idx=-1):
                    break

        matrix = [
            flat_grid[0:3],
            flat_grid[3:6],
            flat_grid[6:9]
        ]
        
        return matrix, lines_won

    # --- MAIN EXECUTION ---

    def execute_spin(self) -> Tuple[List[List[str]], Decimal, bool, List[int], int, int]:
        """Orchestrator method required by BaseSlotEngine."""
        gjp_won = False
        win_amount = Decimal('0.0')
        free_spins_awarded = 0
        multiplier = 1
        result_symbol = None

        # Determine machine temperature based on GJP proximity
        is_hot = float(self.pool.current_value) >= float(self.pool.hot_trigger)

        # 1. Lottery Phase
        if self._roll_gjp():
            result_symbol = 'GJP'
            gjp_won = True
        else:
            result_symbol = self._roll_base_game(is_hot)

        # 2. Payout Phase
        if result_symbol == 'Replay':
            free_spins_awarded = 1
        elif result_symbol and result_symbol != 'GJP':
            win_amount = self.bet_amount * self.PAYOUTS[result_symbol]

        # 3. Visual Grid Compilation Phase
        matrix, lines_won = self._generate_grid(result_symbol)

        return matrix, win_amount, gjp_won, lines_won, free_spins_awarded, multiplier

    def _force_jackpot_matrix(self) -> List[List[str]]:
        """Used by the base engine to guarantee a GJP visual display on override."""
        return [['GJP', 'GJP', 'GJP'], ['Cherry', 'Bell', 'Melon'], ['Melon', '7', 'LOGO']]