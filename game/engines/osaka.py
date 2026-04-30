import random
from decimal import Decimal
from .base import BaseSlotEngine

class OsakaEngine(BaseSlotEngine):
    """
    Sector 03: Osaka Neon
    Algorithm: Polarizer Bias + Random Neon Multipliers
    """
    PAYOUTS = {
        'LOGO': Decimal('200.0'), '7': Decimal('100.0'), 'Melon': Decimal('30.0'),
        'Bell': Decimal('15.0'), 'Cherry': Decimal('5.0'), 'Replay': Decimal('1.0')
    }
    WEIGHTS_BASE = [0.005, 0.4, 1.5, 6, 12, 30, 50.095]
    HOT_WEIGHT_BOOST = 0.1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.polarizer_active = False

    def generate_matrix(self, force_gjp=False, is_hot=False):
        if not force_gjp and random.random() < 0.15:
            self.polarizer_active = True
            polar_weights = [0.01, 2.0, 5.0, 0, 0, 0, 92.99]
            if is_hot: polar_weights[0] += self.HOT_WEIGHT_BOOST
            return [[random.choices(self.SYMBOLS, weights=polar_weights)[0] for _ in range(3)] for _ in range(3)]
            
        self.polarizer_active = False
        return super().generate_matrix(force_gjp, is_hot)

    def calculate_win(self, matrix):
        win_amount, gjp_won, lines_won, free_spins, multiplier = super().calculate_win(matrix)
        
        # If the Polarizer triggered AND the user won, apply a random multiplier
        if self.polarizer_active and win_amount > 0 and not gjp_won:
            multiplier = random.choice([2, 3, 5])
            
        return win_amount, gjp_won, lines_won, free_spins, multiplier

    def _force_jackpot_matrix(self):
        return [['LOGO', 'Melon', '7'], ['GJP', 'GJP', 'GJP'], ['Bell', 'Replay', 'Cherry']]