from datetime import timedelta

from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

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

    GRADE_CHOICES = (
        ("A", "Excellent"),
        ("B", "Good"),
        ("C", "Average"),
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

    # KPI Tracking Fields
    quoted_at = models.DateTimeField(null=True, blank=True, help_text="When inquiry was quoted")
    success_at = models.DateTimeField(null=True, blank=True, help_text="When inquiry was successful")
    failed_at = models.DateTimeField(null=True, blank=True, help_text="When inquiry failed")

    # KPI Durations (calculated automatically)
    quote_time = models.DurationField(default=timedelta(), help_text="Business hours from creation to quote")
    resolution_time = models.DurationField(default=timedelta(), help_text="Business hours from quote to resolution")

    # KPI Grades (calculated automatically)
    quote_grade = models.CharField(
        max_length=1,
        choices=GRADE_CHOICES,
        null=True,
        blank=True,
        help_text="Response time grade: A (≤60hrs), B (≤84hrs), C (>84hrs)"
    )
    completion_grade = models.CharField(
        max_length=1,
        choices=GRADE_CHOICES,
        null=True,
        blank=True,
        help_text="Completion time grade: A (≤120hrs), B (≤168hrs), C (>168hrs)"
    )

    # KPI Control Fields
    auto_completion = models.BooleanField(
        default=False,
        help_text="Skip automatic KPI calculation for this inquiry"
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Lock inquiry from KPI recalculation"
    )

    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["client"]),
            # KPI-related indexes
            models.Index(fields=["sales_manager", "-created_at"]),
            models.Index(fields=["quoted_at"]),
            models.Index(fields=["success_at"]),
            models.Index(fields=["failed_at"]),
            models.Index(fields=["is_new_customer"]),
            models.Index(fields=["quote_grade"]),
            models.Index(fields=["completion_grade"]),
        ]

    def clean(self):
        """Validate that at least text or attachment is provided."""
        super().clean()

        has_text = bool(self.text and self.text.strip())
        has_attachment = bool(self.attachment)

        if not has_text and not has_attachment:
            raise ValidationError("Must provide either text or attachment (or both).")

    def save(self, *args, **kwargs):
        """Override save to call clean validation."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        has_text = bool(self.text and self.text.strip())
        has_attachment = bool(self.attachment)

        if has_text and has_attachment:
            content_type = "text + file"
        elif has_attachment:
            content_type = "file"
        else:
            content_type = "text"

        return f"Inquiry from {self.client} - {self.status} ({content_type})"

    # KPI Business Logic Methods
    def quote(self, quoted_at: timezone.datetime = None) -> None:
        """Mark inquiry as quoted and calculate KPI metrics"""
        from .services import InquiryKPIServices
        InquiryKPIServices.quote_inquiry(inquiry=self, quoted_at=quoted_at)
        self.refresh_from_db()

    def mark_success(self, success_at: timezone.datetime = None) -> None:
        """Mark inquiry as successful and calculate KPI metrics"""
        from .services import InquiryKPIServices
        InquiryKPIServices.complete_inquiry_success(inquiry=self, success_at=success_at)
        self.refresh_from_db()

    def mark_failed(self, failed_at: timezone.datetime = None) -> None:
        """Mark inquiry as failed and calculate KPI metrics"""
        from .services import InquiryKPIServices
        InquiryKPIServices.complete_inquiry_failed(inquiry=self, failed_at=failed_at)
        self.refresh_from_db()

    def recalculate_kpi(self, force: bool = False) -> None:
        """Recalculate KPI metrics for this inquiry"""
        from .services import InquiryKPIServices
        InquiryKPIServices.recalculate_kpi_metrics(inquiry=self, force=force)
        self.refresh_from_db()

    def lock_kpi(self) -> None:
        """Lock inquiry from KPI recalculation"""
        from .services import InquiryKPIServices
        InquiryKPIServices.lock_inquiry_kpi(inquiry=self)
        self.refresh_from_db()

    def unlock_kpi(self) -> None:
        """Unlock inquiry to allow KPI recalculation"""
        from .services import InquiryKPIServices
        InquiryKPIServices.unlock_inquiry_kpi(inquiry=self)
        self.refresh_from_db()

    def set_auto_completion(self, enabled: bool = True) -> None:
        """Enable/disable auto-completion to skip KPI calculations"""
        from .services import InquiryKPIServices
        InquiryKPIServices.set_auto_completion(inquiry=self, auto_completion=enabled)
        self.refresh_from_db()

    @property
    def kpi_quote_points(self) -> int:
        """Get KPI points for quote grade"""
        from .utils import get_grade_points
        return get_grade_points(self.quote_grade)

    @property
    def kpi_completion_points(self) -> int:
        """Get KPI points for completion grade"""
        from .utils import get_grade_points
        return get_grade_points(self.completion_grade)

    @property
    def total_kpi_points(self) -> int:
        """Get total KPI points (quote + completion)"""
        return self.kpi_quote_points + self.kpi_completion_points

    @property
    def is_completed(self) -> bool:
        """Check if inquiry is in a completed state"""
        return self.status in ["success", "failed"]

    @property
    def is_processed(self) -> bool:
        """Check if inquiry has been processed (not pending)"""
        return self.status != "pending"

    @property
    def kpi_status_display(self) -> str:
        """Get human-readable KPI status"""
        if self.is_locked:
            return "🔒 Locked"
        elif self.auto_completion:
            return "⚡ Auto-completion"
        elif not self.is_processed:
            return "⏳ Pending"
        else:
            quote_display = f"Quote: {self.quote_grade or 'N/A'}"
            completion_display = f"Completion: {self.completion_grade or 'N/A'}"
            return f"{quote_display}, {completion_display}"


# KPI Signal Handlers for automatic calculation
@receiver(pre_save, sender=Inquiry)
def update_inquiry_kpi_on_status_change(sender, instance, **kwargs):
    """
    Signal handler to automatically update KPI metrics when inquiry status changes
    """
    # Skip if inquiry is locked or auto_completion is enabled
    if instance.is_locked or instance.auto_completion:
        return

    # Import here to avoid circular imports
    from .utils import (
        calculate_completion_grade,
        calculate_quote_grade,
        get_business_hours_between,
    )

    # Only process if this is an existing instance (has pk)
    if instance.pk is not None:
        try:
            old_instance = Inquiry.objects.get(pk=instance.pk)
        except Inquiry.DoesNotExist:
            # Instance doesn't exist yet, treat as new
            old_instance = None
    else:
        old_instance = None

    current_time = timezone.now()

    # Handle status change from pending to quoted
    if (
        instance.status == "quoted" and
        (old_instance is None or old_instance.status != "quoted")
    ):
        # Set quoted timestamp if not already set
        if not instance.quoted_at:
            instance.quoted_at = current_time

        # Calculate quote time and grade
        if instance.created_at and instance.quoted_at:
            instance.quote_time = get_business_hours_between(
                instance.created_at, instance.quoted_at
            )
            instance.quote_grade = calculate_quote_grade(instance.quote_time)

    # Handle status change from quoted to success
    elif (
        instance.status == "success" and
        (old_instance is None or old_instance.status != "success")
    ):
        # Set success timestamp if not already set
        if not instance.success_at:
            instance.success_at = current_time

        # Calculate resolution time and completion grade
        if instance.quoted_at and instance.success_at:
            instance.resolution_time = get_business_hours_between(
                instance.quoted_at, instance.success_at
            )
            instance.completion_grade = calculate_completion_grade(instance.resolution_time)

        # Clear failed_at if previously set
        instance.failed_at = None

    # Handle status change from quoted to failed
    elif (
        instance.status == "failed" and
        (old_instance is None or old_instance.status != "failed")
    ):
        # Set failed timestamp if not already set
        if not instance.failed_at:
            instance.failed_at = current_time

        # Calculate resolution time and completion grade
        if instance.quoted_at and instance.failed_at:
            instance.resolution_time = get_business_hours_between(
                instance.quoted_at, instance.failed_at
            )
            instance.completion_grade = calculate_completion_grade(instance.resolution_time)

        # Clear success_at if previously set
        instance.success_at = None


@receiver(post_save, sender=Inquiry)
def finalize_inquiry_kpi_calculation(sender, instance, created, **kwargs):
    """
    Post-save signal to finalize KPI calculations and handle any cleanup
    """
    # Skip if inquiry is locked or auto_completion is enabled
    if instance.is_locked or instance.auto_completion:
        return

    # For new inquiries created directly with quoted/success/failed status
    # The pre_save signal handles most cases, this is for edge cases
    if created and instance.status != "pending":
        from .utils import (
            calculate_completion_grade,
            calculate_quote_grade,
            get_business_hours_between,
        )

        needs_update = False
        update_fields = []

        # Handle directly created quoted inquiry
        if instance.status == "quoted" and not instance.quote_grade and instance.created_at:
            if not instance.quoted_at:
                instance.quoted_at = instance.created_at
                update_fields.append('quoted_at')

            instance.quote_time = get_business_hours_between(
                instance.created_at, instance.quoted_at
            )
            instance.quote_grade = calculate_quote_grade(instance.quote_time)
            update_fields.extend(['quote_time', 'quote_grade'])
            needs_update = True

        # Handle directly created completed inquiry
        elif instance.status in ["success", "failed"] and not instance.completion_grade:
            if instance.status == "success" and not instance.success_at:
                instance.success_at = instance.created_at
                update_fields.append('success_at')
            elif instance.status == "failed" and not instance.failed_at:
                instance.failed_at = instance.created_at
                update_fields.append('failed_at')

            # Ensure quote data exists
            if not instance.quoted_at:
                instance.quoted_at = instance.created_at
                update_fields.append('quoted_at')

            if not instance.quote_grade:
                instance.quote_time = timedelta()  # Same day quote
                instance.quote_grade = calculate_quote_grade(instance.quote_time)
                update_fields.extend(['quote_time', 'quote_grade'])

            # Calculate completion metrics
            completion_timestamp = instance.success_at or instance.failed_at
            if completion_timestamp and instance.quoted_at:
                instance.resolution_time = get_business_hours_between(
                    instance.quoted_at, completion_timestamp
                )
                instance.completion_grade = calculate_completion_grade(instance.resolution_time)
                update_fields.extend(['resolution_time', 'completion_grade'])
                needs_update = True

        # Update if needed (avoid infinite recursion with update_fields)
        if needs_update and update_fields:
            Inquiry.objects.filter(pk=instance.pk).update(**{
                field: getattr(instance, field) for field in update_fields
            })
