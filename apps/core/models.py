from django.db import models


class TimeStampModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at fields
    that can be inherited by other models for automatic timestamp tracking.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
