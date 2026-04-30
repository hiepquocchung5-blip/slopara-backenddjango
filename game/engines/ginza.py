import random
from decimal import Decimal
from .base import BaseSlotEngine

class GinzaEngine(BaseSlotEngine):
    """
    Sector 05: Ginza Gold
    Algorithm: Extreme Volatility. Brutal near-misses, but 7s award huge Free Spins and LOGO pays massive base.
    """
    PAYOUTS = {
        'LOGO': Decimal('1000.0'), '7': Decimal('100.0'), 'Melon': Decimal('50.0'),
        'Bell': Decimal('10.0'), 'Cherry': Decimal('5.0'), 'Replay': Decimal('0.0') # Dead Replays
    }
    WEIGHTS_BASE = [0.001, 0.1, 0.5, 2, 8, 20, 69.399]
    HOT_WEIGHT_BOOST = 0.01

    def generate_matrix(self, force_gjp=False, is_hot=False):
        matrix = super().generate_matrix(force_gjp, is_hot)
        
        # 10% chance to tease the 1000x LOGO payout but fail
        if not force_gjp and random.random() < 0.10:
            matrix[1][0] = 'LOGO'
            matrix[1][1] = 'LOGO'
            matrix[1][2] = random.choice(['Replay', 'Cherry', 'Bell'])
            
        return matrix

    def calculate_win(self, matrix):
        win_amount, gjp_won, lines_won, free_spins, multiplier = super().calculate_win(matrix)
        
        # In Ginza, 7-7-7 awards 25 Free Spins (Massive Fever Mode)
        lines = [matrix[0], matrix[1], matrix[2], [matrix[0][0], matrix[1][1], matrix[2][2]], [matrix[0][2], matrix[1][1], matrix[2][0]]]
        for idx in lines_won:
            if lines[idx][0] == '7':
                free_spins += 25
                
        return win_amount, gjp_won, lines_won, free_spins, multiplier

    def _force_jackpot_matrix(self):
        return [['LOGO', 'LOGO', 'LOGO'], ['GJP', 'GJP', 'GJP'], ['LOGO', 'LOGO', 'LOGO']]