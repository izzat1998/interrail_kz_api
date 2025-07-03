from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class CustomUser(AbstractUser):
    USER_TYPES = [
        ('customer', 'Customer'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default='manager',
    )
    telegram_id = models.CharField(max_length=50, null=True, blank=True)
    telegram_username = models.CharField(max_length=100, null=True, blank=True)
    telegram_access = models.BooleanField(default=False)
    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"