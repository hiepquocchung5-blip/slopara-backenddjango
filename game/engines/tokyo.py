import random
from decimal import Decimal
from .base import BaseSlotEngine

class TokyoEngine(BaseSlotEngine):
    """
    Sector 04: Tokyo Cyber
    Algorithm: High Volatility. High Dead Spin Rate funding Massive Base Multipliers.
    """
    PAYOUTS = {
        'LOGO': Decimal('100.0'), '7': Decimal('50.0'), 'Melon': Decimal('20.0'),
        'Bell': Decimal('10.0'), 'Cherry': Decimal('5.0'), 'Replay': Decimal('2.0')
    }
    WEIGHTS_BASE = [0.002, 0.2, 1.0, 4, 10, 25, 59.798]
    HOT_WEIGHT_BOOST = 0.05

    def generate_matrix(self, force_gjp=False, is_hot=False):
        # 30% chance of an absolute dead spin to fund the multipliers
        if not force_gjp and random.random() < 0.30:
            return [['Replay', 'Cherry', 'Bell'], ['Bell', 'Replay', 'Melon'], ['Cherry', 'Melon', 'Replay']]
        return super().generate_matrix(force_gjp, is_hot)

    def calculate_win(self, matrix):
        win_amount, gjp_won, lines_won, free_spins, multiplier = super().calculate_win(matrix)
        
        # Any win on Tokyo has a chance to explode with a massive multiplier
        if win_amount > 0 and not gjp_won:
            roll = random.random()
            if roll < 0.01: multiplier = 50   # 1% chance for 50x
            elif roll < 0.05: multiplier = 20 # 4% chance for 20x
            elif roll < 0.15: multiplier = 10 # 10% chance for 10x
            
        return win_amount, gjp_won, lines_won, free_spins, multiplier

    def _force_jackpot_matrix(self):
        return [['Replay', 'Replay', 'Replay'], ['GJP', 'GJP', 'GJP'], ['7', '7', '7']]