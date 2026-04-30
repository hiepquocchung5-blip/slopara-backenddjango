import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from game.engines import get_engine

class DummyPool:
    """Mock object to bypass database queries during simulation"""
    def __init__(self):
        self.current_value = Decimal('1000000.0')
        self.must_hit_value = Decimal('2000000.0')
        self.hot_trigger = Decimal('1500000.0')
        self.contribution_rate = Decimal('0.01')
        self.base_seed = Decimal('1000000.0')

class Command(BaseCommand):
    help = 'Simulates millions of spins in memory to verify engine RTP and volatility.'

    def add_arguments(self, parser):
        parser.add_argument('--island', type=int, default=1, help='Island ID (1=Kyoto, 2=Okinawa, etc)')
        parser.add_argument('--spins', type=int, default=100000, help='Number of spins to simulate')
        parser.add_argument('--bet', type=str, default='1000', help='Bet amount per spin')

    def handle(self, *args, **options):
        island_id = options['island']
        spins = options['spins']
        bet_amount = Decimal(options['bet'])
        
        EngineClass = get_engine(island_id)
        pool = DummyPool()
        engine = EngineClass(island=None, pool=pool, bet_amount=bet_amount)

        self.stdout.write(self.style.WARNING(f"\nInitializing {EngineClass.__name__}..."))
        self.stdout.write(f"Simulating {spins:,} spins at {bet_amount} MMK each.\n")

        total_wagered = Decimal('0')
        total_won = Decimal('0')
        gjp_hits = 0
        winning_spins = 0

        start_time = time.time()

        for _ in range(spins):
            total_wagered += bet_amount
            
            # Using the exact same logic as process_spin
            matrix = engine.generate_matrix(force_gjp=False, is_hot=False)
            win_amount, gjp_won, lines_won = engine.calculate_win(matrix)

            if gjp_won:
                gjp_hits += 1
                win_amount += pool.current_value
                # Reset mock pool
                pool.current_value = pool.base_seed
            else:
                # Add contribution to mock pool
                pool.current_value += (bet_amount * pool.contribution_rate)

            total_won += win_amount
            if win_amount > 0:
                winning_spins += 1

        elapsed = time.time() - start_time
        rtp = (total_won / total_wagered) * 100 if total_wagered > 0 else 0
        hit_rate = (winning_spins / spins) * 100

        self.stdout.write(self.style.SUCCESS(f"Simulation Complete in {elapsed:.2f} seconds."))
        self.stdout.write("-" * 40)
        self.stdout.write(f"Total Wagered:  {total_wagered:,.2f} MMK")
        self.stdout.write(f"Total Paid Out: {total_won:,.2f} MMK")
        self.stdout.write(f"House Profit:   {total_wagered - total_won:,.2f} MMK")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Hit Rate:       {hit_rate:.2f}%")
        self.stdout.write(f"GJP Hits:       {gjp_hits}")
        
        # Color code RTP output
        rtp_str = f"Actual RTP:     {rtp:.2f}%"
        if rtp > 100:
            self.stdout.write(self.style.ERROR(rtp_str + " (WARNING: PLAYER ADVANTAGE)"))
        elif rtp > 95:
            self.stdout.write(self.style.WARNING(rtp_str + " (HIGH PAYOUT)"))
        else:
            self.stdout.write(self.style.SUCCESS(rtp_str + " (PROFITABLE)"))
        self.stdout.write("\n")