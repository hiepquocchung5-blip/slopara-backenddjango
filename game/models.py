from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Island(models.Model):
    name = models.CharField(max_length=50, unique=True)
    min_lifetime_deposit = models.DecimalField(max_digits=12, decimal_places=2)
    total_machines = models.IntegerField(default=900)
    floors = models.IntegerField(default=10)
    
    def __str__(self):
        return self.name

class GJP_Pool(models.Model):
    island = models.OneToOneField(Island, on_delete=models.CASCADE, related_name='gjp_pool')
    current_value = models.DecimalField(max_digits=12, decimal_places=2)
    base_seed = models.DecimalField(max_digits=12, decimal_places=2)
    hot_trigger = models.DecimalField(max_digits=12, decimal_places=2)
    must_hit_value = models.DecimalField(max_digits=12, decimal_places=2)
    contribution_rate = models.DecimalField(max_digits=5, decimal_places=4)

    def __str__(self):
        return f"{self.island.name} GJP - Cur: {self.current_value}"

class Machine(models.Model):
    island = models.ForeignKey(Island, on_delete=models.CASCADE, related_name='machines')
    floor = models.IntegerField()
    machine_number = models.IntegerField()
    is_occupied = models.BooleanField(default=False)
    current_player = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('island', 'floor', 'machine_number')
        ordering = ['floor', 'machine_number']

class SpinHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spins')
    island = models.ForeignKey(Island, on_delete=models.SET_NULL, null=True)
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True) # FIXED: Added Machine
    bet_amount = models.DecimalField(max_digits=10, decimal_places=2)
    win_amount = models.DecimalField(max_digits=12, decimal_places=2)
    symbols_matrix = models.JSONField() 
    lines_won = models.JSONField(default=list) 
    is_gjp_win = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
        ]

# FIXED: Added PlayerGameState to track persistent Fever Mode / Free Spins
class PlayerGameState(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_states')
    island = models.ForeignKey(Island, on_delete=models.CASCADE)
    free_spins_remaining = models.IntegerField(default=0)
    locked_bet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('user', 'island')