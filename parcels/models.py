from django.db import models
from django.utils import timezone
import uuid
import random
import string


def generate_tracking_id():
    prefix = "PRCL"
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{suffix}"


class Parcel(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_id = models.IntegerField()  # references user-service (customer)
    receiver_name = models.CharField(max_length=100)
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    assigned_driver_id = models.IntegerField(null=True, blank=True)  # from user-service (driver)
    tracking_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = generate_tracking_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Parcel {self.tracking_id or self.id} - {self.status}"
