import django_filters
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr="icontains")
    username = django_filters.CharFilter(lookup_expr="icontains")
    first_name = django_filters.CharFilter(lookup_expr="icontains")
    last_name = django_filters.CharFilter(lookup_expr="icontains")
    user_type = django_filters.ChoiceFilter(choices=User.USER_TYPES)
    is_active = django_filters.BooleanFilter()
    telegram_username = django_filters.CharFilter(lookup_expr="icontains")

    # Search across multiple fields
    search = django_filters.CharFilter(method="filter_search")

    # Filter managers who have created inquiries
    inquiry_related = django_filters.BooleanFilter(method="filter_inquiry_related")

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "user_type",
            "is_active",
            "telegram_username",
            "search",
            "inquiry_related",
        ]

    def filter_search(self, queryset, name, value):
        """
        Search across multiple fields
        """
        if not value:
            return queryset

        return queryset.filter(
            models.Q(username__icontains=value)
            | models.Q(email__icontains=value)
            | models.Q(first_name__icontains=value)
            | models.Q(last_name__icontains=value)
            | models.Q(telegram_username__icontains=value)
        )

    def filter_inquiry_related(self, queryset, name, value):
        """
        Filter managers who have created inquiries
        """
        if value:
            # Filter users who have related inquiries (sales_inquiries related_name)
            return queryset.filter(sales_inquiries__isnull=False).distinct()
        return queryset
