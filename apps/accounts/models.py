from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    USER_TYPES = [
        ("customer", "Customer"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default="customer",
    )
    phone = models.CharField(max_length=20, null=True, blank=True, unique=True)
    telegram_id = models.CharField(max_length=50, null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=100, null=True, blank=True)
    telegram_access = models.BooleanField(default=False)
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["-date_joined"]),
            models.Index(fields=["user_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["telegram_id"]),
        ]
