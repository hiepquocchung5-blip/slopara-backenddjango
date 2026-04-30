import random
from decimal import Decimal
from .base import BaseSlotEngine

class OkinawaEngine(BaseSlotEngine):
    """
    Sector 02: Okinawa Tropic
    Algorithm: Medium Volatility with "Symbol Clumping" (Stacked Reels).
    """
    
    PAYOUTS = {
        'LOGO': Decimal('150.0'), '7': Decimal('75.0'), 'Melon': Decimal('25.0'),
        'Bell': Decimal('5.0'), 'Cherry': Decimal('2.0'), 'Replay': Decimal('0.5')
    }
    
    WEIGHTS_BASE = [0.005, 0.5, 2, 8, 15, 35, 39.495]
    HOT_WEIGHT_BOOST = 0.2

    def generate_matrix(self, force_gjp=False, is_hot=False):
        """
        Custom Okinawa Algorithm:
        10% chance to 'clump' a reel (force an entire vertical column to be the same symbol).
        This creates high visual excitement and allows for massive multi-line combo wins, 
        balanced by the slightly lower base payouts for minor symbols.
        """
        matrix = super().generate_matrix(force_gjp, is_hot)
        
        if not force_gjp and random.random() < 0.10:
            target_col = random.randint(0, 2)
            # Pick a symbol based on the island's natural weights
            clump_symbol = random.choices(self.SYMBOLS, weights=self.WEIGHTS_BASE)[0]
            
            # Stack the reel
            matrix[0][target_col] = clump_symbol
            matrix[1][target_col] = clump_symbol
            matrix[2][target_col] = clump_symbol
            
        return matrix

    def _force_jackpot_matrix(self):
        return [
            ['7', '7', '7'],
            ['GJP', 'GJP', 'GJP'],
            ['Bell', 'Bell', 'Bell']
        ]