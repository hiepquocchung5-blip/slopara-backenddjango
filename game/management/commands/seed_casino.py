from django.core.management.base import BaseCommand
from django.db import transaction
from game.models import Island, GJP_Pool, Machine

class Command(BaseCommand):
    help = 'Seeds the database with standard Casino Islands, GJP Pools, and Machines.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        islands_data = [
            {'name': 'Kyoto Zen', 'ltd': 0, 'floors': 5, 'base_gjp': 500000},
            {'name': 'Okinawa Tropic', 'ltd': 50000, 'floors': 5, 'base_gjp': 1000000},
            {'name': 'Osaka Neon', 'ltd': 250000, 'floors': 5, 'base_gjp': 2500000},
            {'name': 'Tokyo Cyber', 'ltd': 1000000, 'floors': 5, 'base_gjp': 5000000},
            {'name': 'Ginza Gold', 'ltd': 5000000, 'floors': 5, 'base_gjp': 10000000},
        ]

        self.stdout.write("Wiping old floor data...")
        Machine.objects.all().delete()
        GJP_Pool.objects.all().delete()
        Island.objects.all().delete()

        self.stdout.write("Constructing Islands & Pools...")
        for data in islands_data:
            island = Island.objects.create(
                name=data['name'], 
                min_lifetime_deposit=data['ltd'], 
                total_machines=data['floors'] * 100, 
                floors=data['floors']
            )
            
            GJP_Pool.objects.create(
                island=island,
                current_value=data['base_gjp'],
                base_seed=data['base_gjp'],
                hot_trigger=data['base_gjp'] * 1.5,
                must_hit_value=data['base_gjp'] * 2.0,
                contribution_rate=0.005 # 0.5% of every bet goes to GJP
            )

            machines = []
            for floor in range(1, data['floors'] + 1):
                for num in range(1, 101):
                    machines.append(Machine(island=island, floor=floor, machine_number=num))
            
            Machine.objects.bulk_create(machines)
            self.stdout.write(f"✓ Built {island.name} with {len(machines)} machines.")

        self.stdout.write(self.style.SUCCESS("Successfully seeded Casino Floor!"))