import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from game.models import Island, GJP_Pool, Machine

class Command(BaseCommand):
    help = 'Wipes existing floor data and seeds the 5 master Casino Islands with exact GJP mechanics.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing Casino Floor Seeding Protocol...")

        # ISLAND & GJP ARCHITECTURE MAP
        # Note: Contribution Rates are converted from % (e.g., 0.05% -> 0.0005)
        ISLANDS_DATA = [
            {
                "name": "KYOTO ZEN",
                "min_ltd": 0, # Unlocked for everyone
                "total_machines": 900,
                "gjp": { "current": 2000000, "base": 2500000, "must_hit": 5000000, "rate": 0.0005 }
            },
            {
                "name": "OKINAWA TROPIC",
                "min_ltd": 50000, # Elite Tier
                "total_machines": 720,
                "gjp": { "current": 7000000, "base": 8000000, "must_hit": 12500000, "rate": 0.0006 }
            },
            {
                "name": "OSAKA NEON",
                "min_ltd": 500000, # Epic Tier
                "total_machines": 540,
                "gjp": { "current": 12000000, "base": 14100000, "must_hit": 19000000, "rate": 0.0007 }
            },
            {
                "name": "TOKYO CYBER",
                "min_ltd": 5000000, # Mythic Tier
                "total_machines": 360,
                "gjp": { "current": 19000000, "base": 23000000, "must_hit": 35000000, "rate": 0.0008 }
            },
            {
                "name": "GINZA GOLD",
                "min_ltd": 50000000, # Immortal Tier
                "total_machines": 180,
                "gjp": { "current": 30000000, "base": 37000000, "must_hit": 55000000, "rate": 0.0009 }
            }
        ]

        MACHINES_PER_FLOOR = 90

        try:
            with transaction.atomic():
                self.stdout.write("Purging legacy floor data...")
                Machine.objects.all().delete()
                GJP_Pool.objects.all().delete()
                Island.objects.all().delete()

                for data in ISLANDS_DATA:
                    floors = data["total_machines"] // MACHINES_PER_FLOOR
                    
                    # 1. Create Island
                    island = Island.objects.create(
                        name=data["name"],
                        min_lifetime_deposit=Decimal(str(data["min_ltd"])),
                        total_machines=data["total_machines"],
                        floors=floors
                    )
                    self.stdout.write(f"Created Island: {island.name} ({floors} Floors)")

                    # 2. Bind GJP Pool
                    gjp_data = data["gjp"]
                    # Calculate a logical hot_trigger (midpoint between Base and Must-Hit)
                    hot_trigger = gjp_data["base"] + ((gjp_data["must_hit"] - gjp_data["base"]) * 0.5)

                    GJP_Pool.objects.create(
                        island=island,
                        current_value=Decimal(str(gjp_data["current"])),
                        base_seed=Decimal(str(gjp_data["base"])),
                        hot_trigger=Decimal(str(hot_trigger)),
                        must_hit_value=Decimal(str(gjp_data["must_hit"])),
                        contribution_rate=Decimal(str(gjp_data["rate"]))
                    )

                    # 3. Fabricate Machines (Bulk Creation for Performance)
                    machines_to_create = []
                    machine_counter = 1
                    
                    for floor in range(1, floors + 1):
                        for _ in range(MACHINES_PER_FLOOR):
                            machines_to_create.append(
                                Machine(
                                    island=island,
                                    floor=floor,
                                    machine_number=machine_counter
                                )
                            )
                            machine_counter += 1

                    Machine.objects.bulk_create(machines_to_create)
                    self.stdout.write(f"  -> Deployed {len(machines_to_create)} machines for {island.name}.")

            self.stdout.write(self.style.SUCCESS('SUCCESS: Casino Floor Initialized. 2,700 Units Online.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'CRITICAL FAILURE: {str(e)}'))
            sys.exit(1)