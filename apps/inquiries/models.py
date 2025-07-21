from ckeditor.fields import RichTextField
from django.db import models

from apps.accounts.models import CustomUser
from apps.core.models import TimeStampModel

# Create your models here.


class Inquiry(TimeStampModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("quoted", "Quoted"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    client = models.CharField(max_length=255, blank=True, default="")
    text = RichTextField()
    comment = RichTextField(blank=True, default="")
    sales_manager = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="sales_inquiries",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0]
    )
    is_new_customer = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["client"]),
        ]

    def __str__(self):
        return f"Inquiry from {self.client} - {self.status}"
