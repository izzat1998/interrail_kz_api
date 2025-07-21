import django_filters
from django.db import models

from .models import Inquiry


class InquiryFilter(django_filters.FilterSet):
    client = django_filters.CharFilter(lookup_expr="icontains")
    text = django_filters.CharFilter(lookup_expr="icontains")
    comment = django_filters.CharFilter(lookup_expr="icontains")

    status = django_filters.MultipleChoiceFilter(choices=Inquiry.STATUS_CHOICES)
    is_new_customer = django_filters.BooleanFilter()
    sales_manager_id = django_filters.NumberFilter()

    # Search across multiple fields
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "client",
            "text",
            "comment",
            "status",
            "is_new_customer",
            "sales_manager",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        """
        Search across multiple fields
        """
        if not value:
            return queryset

        return queryset.filter(
            models.Q(client__icontains=value)
            | models.Q(text__icontains=value)
            | models.Q(comment__icontains=value)
        )
