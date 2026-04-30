from decimal import Decimal
import random

class BaseSlotEngine:
    SYMBOLS = ['GJP', 'LOGO', '7', 'Melon', 'Bell', 'Cherry', 'Replay']
    PAYOUTS = {}
    WEIGHTS_BASE = []
    HOT_WEIGHT_BOOST = 0.0

    def __init__(self, island, pool, bet_amount):
        self.island = island
        self.pool = pool
        self.bet_amount = Decimal(str(bet_amount))

    def generate_matrix(self, force_gjp=False, is_hot=False):
        if force_gjp:
            weights = [100, 0, 0, 0, 0, 0, 0]
        else:
            weights = list(self.WEIGHTS_BASE)
            if is_hot: weights[0] += self.HOT_WEIGHT_BOOST
                
        return [[random.choices(self.SYMBOLS, weights=weights)[0] for _ in range(3)] for _ in range(3)]

    def calculate_win(self, matrix):
        lines = [
            matrix[0], matrix[1], matrix[2], 
            [matrix[0][0], matrix[1][1], matrix[2][2]], 
            [matrix[0][2], matrix[1][1], matrix[2][0]]  
        ]
        win_amount = Decimal('0.0')
        gjp_won = False
        lines_won = []
        free_spins_awarded = 0
        multiplier = 1 # NEW: Base multiplier support
        
        for idx, line in enumerate(lines):
            if line[0] == line[1] == line[2]:
                sym = line[0]
                if sym == 'GJP':
                    gjp_won = True
                    lines_won.append(idx)
                elif sym in self.PAYOUTS:
                    win_amount += self.bet_amount * self.PAYOUTS[sym]
                    lines_won.append(idx)
                    
        return win_amount, gjp_won, lines_won, free_spins_awarded, multiplier
        
    def execute_spin(self):
        force_gjp = self.pool.current_value >= self.pool.must_hit_value
        is_hot = self.pool.current_value >= self.pool.hot_trigger

        matrix = self.generate_matrix(force_gjp, is_hot)
        win_amount, gjp_won, lines_won, free_spins_awarded, multiplier = self.calculate_win(matrix)

        if force_gjp and not gjp_won:
            matrix = self._force_jackpot_matrix()
            win_amount, gjp_won, lines_won, free_spins_awarded, multiplier = self.calculate_win(matrix)

        # Apply final multiplier to the base win
        win_amount = win_amount * Decimal(str(multiplier))

        return matrix, win_amount, gjp_won, lines_won, free_spins_awarded, multiplier

    def _force_jackpot_matrix(self):
        raise NotImplementedError("Child engine must define a visual forced jackpot layout.")