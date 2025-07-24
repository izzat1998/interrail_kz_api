from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import CustomUser
from apps.core.models import TimeStampModel


# File size validation
def validate_file_size(value):
    """Validate file size limit (10MB)"""
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size > max_size:
        raise ValidationError(f"File too large. Maximum size is {max_size / (1024 * 1024):.0f}MB")


class Inquiry(TimeStampModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("quoted", "Quoted"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    client = models.CharField(max_length=255, blank=True, default="")
    text = RichTextField(blank=True, null=True)
    attachment = models.FileField(
        upload_to="inquiry_attachments/%Y/%m/%d/",
        null=True,
        blank=True,
        validators=[validate_file_size],
    )
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

    def clean(self):
        """Validate that either text or attachment is provided, but not both or neither."""
        super().clean()

        has_text = bool(self.text and self.text.strip())
        has_attachment = bool(self.attachment)

        if has_text and has_attachment:
            raise ValidationError("Cannot provide both text and attachment. Choose one.")

        if not has_text and not has_attachment:
            raise ValidationError("Must provide either text or attachment.")

    def save(self, *args, **kwargs):
        """Override save to call clean validation."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        content_type = "file" if self.attachment else "text"
        return f"Inquiry from {self.client} - {self.status} ({content_type})"
