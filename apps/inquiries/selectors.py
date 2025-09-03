from datetime import datetime, timedelta
from typing import Any

from django.db.models import (
    Case,
    Count,
    IntegerField,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.accounts.models import CustomUser

from .filters import InquiryFilter
from .models import Inquiry
from .utils import calculate_conversion_percentage


class InquirySelectors:
    """
    Selectors for inquiry-related data retrieval
    """

    @staticmethod
    def get_inquiry_instance_by_id(*, inquiry_id: int) -> Inquiry:
        """
        Get inquiry model instance by ID
        """
        return Inquiry.objects.select_related("sales_manager").get(id=inquiry_id)

    @staticmethod
    def get_inquiry_by_id(*, inquiry_id: int) -> dict[str, Any]:
        """
        Get inquiry by ID with error handling and formatting
        """
        inquiry = Inquiry.objects.select_related("sales_manager").get(id=inquiry_id)

        # Format the data similar to accounts app pattern
        return {
            "id": inquiry.id,
            "client": inquiry.client,
            "text": inquiry.text,
            "attachment_url": inquiry.attachment.url if inquiry.attachment else None,
            "attachment_name": inquiry.attachment.name.split('/')[-1] if inquiry.attachment else None,
            "has_attachment": bool(inquiry.attachment),
            "comment": inquiry.comment,
            "status": inquiry.status,
            "status_display": inquiry.get_status_display(),
            "sales_manager": (
                {
                    "id": inquiry.sales_manager.id,
                    "username": inquiry.sales_manager.username,
                    "email": inquiry.sales_manager.email,
                }
                if inquiry.sales_manager
                else None
            ),
            "is_new_customer": inquiry.is_new_customer,
            "created_at": inquiry.created_at,
            "updated_at": inquiry.updated_at,
        }

    @staticmethod
    def get_sales_manager_by_id(*, manager_id: int) -> CustomUser:
        """
        Get sales manager by ID with error handling
        """
        return CustomUser.objects.get(id=manager_id)

    @staticmethod
    def get_sales_manager_by_id_or_telegram(*, manager_id: str | int) -> CustomUser:
        """
        Get sales manager by system ID or telegram ID
        Args:
            manager_id: Can be either system ID (int) or telegram_id (str)
        Returns:
            CustomUser instance
        """
        try:
            # First try to get by telegram_id
            return CustomUser.objects.get(telegram_id=manager_id)
        except CustomUser.DoesNotExist:
            # If not found, try to get by system ID
            return CustomUser.objects.get(id=manager_id)


    @staticmethod
    def get_inquiries_list(
        *, filters: dict[str, Any] | None = None
    ) -> QuerySet[Inquiry]:
        """
        Get filtered and paginated inquiries list
        """
        filters = filters or {}
        qs = Inquiry.objects.select_related("sales_manager").all()
        return InquiryFilter(filters, qs).qs

    @staticmethod
    def get_inquiries_stats() -> dict[str, Any]:
        """
        Get inquiry statistics using a single database query
        """
        from django.db.models import Case, Count, IntegerField, When

        stats = Inquiry.objects.aggregate(
            total_inquiries=Count("id"),
            pending_count=Count(
                Case(
                    When(status="pending", then=1),
                    output_field=IntegerField(),
                )
            ),
            quoted_count=Count(
                Case(
                    When(status="quoted", then=1),
                    output_field=IntegerField(),
                )
            ),
            success_count=Count(
                Case(
                    When(status="success", then=1),
                    output_field=IntegerField(),
                )
            ),
            failed_count=Count(
                Case(
                    When(status="failed", then=1),
                    output_field=IntegerField(),
                )
            ),
            new_customers_count=Count(
                Case(
                    When(is_new_customer=True, then=1),
                    output_field=IntegerField(),
                )
            ),
        )

        stats["conversion_rate"] = (
            stats["success_count"] / stats["total_inquiries"] * 100
            if stats["total_inquiries"] > 0
            else 0
        )

        return stats

    @staticmethod
    def get_manager_kpi_statistics(
        *, manager_id: int,
        date_from: datetime = None,
        date_to: datetime = None
    ) -> dict[str, Any]:
        """
        Get comprehensive KPI statistics for a specific sales manager

        Args:
            manager_id: Sales manager ID
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            Dictionary with manager KPI metrics
        """
        qs = Inquiry.objects.filter(sales_manager_id=manager_id)

        # Apply date filters if provided
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        # Get basic statistics
        stats = qs.aggregate(
            total_inquiries=Count('id'),
            total_pending=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
            total_quoted=Count(Case(When(status='quoted', then=1), output_field=IntegerField())),
            total_success=Count(Case(When(status='success', then=1), output_field=IntegerField())),
            total_failed=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            new_customers=Count(Case(When(is_new_customer=True, then=1), output_field=IntegerField())),

            # KPI Grade Statistics
            quote_grade_a=Count(Case(When(quote_grade='A', then=1), output_field=IntegerField())),
            quote_grade_b=Count(Case(When(quote_grade='B', then=1), output_field=IntegerField())),
            quote_grade_c=Count(Case(When(quote_grade='C', then=1), output_field=IntegerField())),

            completion_grade_a=Count(Case(When(completion_grade='A', then=1), output_field=IntegerField())),
            completion_grade_b=Count(Case(When(completion_grade='B', then=1), output_field=IntegerField())),
            completion_grade_c=Count(Case(When(completion_grade='C', then=1), output_field=IntegerField())),

            # KPI Points Calculation
            total_quote_points=Sum(
                Case(
                    When(quote_grade='A', then=Value(3)),
                    When(quote_grade='B', then=Value(2)),
                    When(quote_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
            total_completion_points=Sum(
                Case(
                    When(completion_grade='A', then=Value(3)),
                    When(completion_grade='B', then=Value(2)),
                    When(completion_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
        )

        # Calculate derived metrics
        stats['processed_inquiries'] = stats['total_inquiries'] - stats['total_pending']
        stats['completed_inquiries'] = stats['total_success'] + stats['total_failed']

        # Conversion rates
        if stats['total_inquiries'] > 0:
            stats['conversion_rate'] = calculate_conversion_percentage(
                stats['total_success'], stats['total_inquiries']
            )
        else:
            stats['conversion_rate'] = 0.0

        if stats['processed_inquiries'] > 0:
            stats['processing_conversion_rate'] = calculate_conversion_percentage(
                stats['total_success'], stats['processed_inquiries']
            )
        else:
            stats['processing_conversion_rate'] = 0.0

        # Lead generation percentage
        if stats['total_inquiries'] > 0:
            stats['lead_generation_rate'] = calculate_conversion_percentage(
                stats['new_customers'], stats['total_inquiries']
            )
        else:
            stats['lead_generation_rate'] = 0.0

        # Average KPI points
        stats['total_kpi_points'] = (stats['total_quote_points'] or 0) + (stats['total_completion_points'] or 0)

        if stats['processed_inquiries'] > 0:
            stats['avg_quote_points'] = (stats['total_quote_points'] or 0) / stats['processed_inquiries']
        else:
            stats['avg_quote_points'] = 0.0

        if stats['completed_inquiries'] > 0:
            stats['avg_completion_points'] = (stats['total_completion_points'] or 0) / stats['completed_inquiries']
            stats['avg_total_points'] = stats['total_kpi_points'] / stats['completed_inquiries']
        else:
            stats['avg_completion_points'] = 0.0
            stats['avg_total_points'] = 0.0

        # Grade distribution percentages
        graded_quotes = stats['quote_grade_a'] + stats['quote_grade_b'] + stats['quote_grade_c']
        if graded_quotes > 0:
            stats['quote_grade_a_pct'] = (stats['quote_grade_a'] / graded_quotes) * 100
            stats['quote_grade_b_pct'] = (stats['quote_grade_b'] / graded_quotes) * 100
            stats['quote_grade_c_pct'] = (stats['quote_grade_c'] / graded_quotes) * 100
        else:
            stats['quote_grade_a_pct'] = stats['quote_grade_b_pct'] = stats['quote_grade_c_pct'] = 0.0

        graded_completions = stats['completion_grade_a'] + stats['completion_grade_b'] + stats['completion_grade_c']
        if graded_completions > 0:
            stats['completion_grade_a_pct'] = (stats['completion_grade_a'] / graded_completions) * 100
            stats['completion_grade_b_pct'] = (stats['completion_grade_b'] / graded_completions) * 100
            stats['completion_grade_c_pct'] = (stats['completion_grade_c'] / graded_completions) * 100
        else:
            stats['completion_grade_a_pct'] = stats['completion_grade_b_pct'] = stats['completion_grade_c_pct'] = 0.0

        return stats

    @staticmethod
    def get_kpi_dashboard_data(
        *, date_from: datetime = None, date_to: datetime = None
    ) -> dict[str, Any]:
        """
        Get comprehensive KPI dashboard data across all managers

        Args:
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            Dictionary with dashboard KPI metrics
        """
        qs = Inquiry.objects.all()

        # Apply date filters if provided
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        # Overall statistics
        overall_stats = qs.aggregate(
            total_inquiries=Count('id'),
            pending_count=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
            quoted_count=Count(Case(When(status='quoted', then=1), output_field=IntegerField())),
            success_count=Count(Case(When(status='success', then=1), output_field=IntegerField())),
            failed_count=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            new_customers_count=Count(Case(When(is_new_customer=True, then=1), output_field=IntegerField())),

            # KPI Points Summary
            total_quote_points=Sum(
                Case(
                    When(quote_grade='A', then=Value(3)),
                    When(quote_grade='B', then=Value(2)),
                    When(quote_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
            total_completion_points=Sum(
                Case(
                    When(completion_grade='A', then=Value(3)),
                    When(completion_grade='B', then=Value(2)),
                    When(completion_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Grade counts for overall performance
            quote_a_count=Count(Case(When(quote_grade='A', then=1), output_field=IntegerField())),
            quote_b_count=Count(Case(When(quote_grade='B', then=1), output_field=IntegerField())),
            quote_c_count=Count(Case(When(quote_grade='C', then=1), output_field=IntegerField())),

            completion_a_count=Count(Case(When(completion_grade='A', then=1), output_field=IntegerField())),
            completion_b_count=Count(Case(When(completion_grade='B', then=1), output_field=IntegerField())),
            completion_c_count=Count(Case(When(completion_grade='C', then=1), output_field=IntegerField())),
        )

        # Calculate conversion and lead generation rates
        if overall_stats['total_inquiries'] > 0:
            overall_stats['conversion_rate'] = calculate_conversion_percentage(
                overall_stats['success_count'], overall_stats['total_inquiries']
            )
            overall_stats['lead_generation_rate'] = calculate_conversion_percentage(
                overall_stats['new_customers_count'], overall_stats['total_inquiries']
            )
        else:
            overall_stats['conversion_rate'] = 0.0
            overall_stats['lead_generation_rate'] = 0.0

        # Manager performance ranking with additional metrics
        manager_performance = qs.filter(
            sales_manager__isnull=False
        ).values(
            'sales_manager_id',
            'sales_manager__username',
            'sales_manager__email',
            'sales_manager__first_name',
            'sales_manager__last_name'
        ).annotate(
            manager_total=Count('id'),
            manager_success=Count(Case(When(status='success', then=1), output_field=IntegerField())),
            manager_pending=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
            manager_quoted=Count(Case(When(status='quoted', then=1), output_field=IntegerField())),
            manager_failed=Count(Case(When(status='failed', then=1), output_field=IntegerField())),

            # Дополнительные метрики для процентов
            quote_grade_a_count=Count(Case(When(quote_grade='A', then=1), output_field=IntegerField())),
            completed_count=Count(Case(When(status__in=['success', 'failed'], then=1), output_field=IntegerField())),
            new_customers_count=Count(Case(When(is_new_customer=True, then=1), output_field=IntegerField())),

            # KPI баллы
            manager_quote_points=Sum(
                Case(
                    When(quote_grade='A', then=Value(3)),
                    When(quote_grade='B', then=Value(2)),
                    When(quote_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
            manager_completion_points=Sum(
                Case(
                    When(completion_grade='A', then=Value(3)),
                    When(completion_grade='B', then=Value(2)),
                    When(completion_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).filter(
            manager_total__gt=0
        ).order_by('-manager_success')

        # Add conversion rate to manager performance and format data
        formatted_performance = []
        for manager in manager_performance:
            # Расчет процентных метрик на основе максимально возможных баллов

            # 1. Процент эффективности по котировкам (актуальные баллы / максимум)
            # Максимум = количество заявок × 3 балла (если все Grade A)
            max_quote_points = manager['manager_total'] * 3
            quote_performance_percentage = (
                (manager['manager_quote_points'] / max_quote_points * 100)
                if max_quote_points > 0 else 0.0
            )

            # 2. Процент эффективности по завершению (актуальные баллы / максимум)
            # Максимум = количество завершенных заявок × 3 балла
            max_completion_points = manager['completed_count'] * 3
            completion_performance_percentage = (
                (manager['manager_completion_points'] / max_completion_points * 100)
                if max_completion_points > 0 else 0.0
            )

            # 3. Процент завершенных заявок (не застрявших в quoted/pending)
            # completion_rate = calculate_conversion_percentage(
            #     manager['completed_count'], manager['manager_total']
            # )

            # 4. Процент конверсии (успешные сделки)
            conversion_rate = calculate_conversion_percentage(
                manager['manager_success'], manager['manager_total']
            )

            # 5. Процент новых клиентов
            new_customers_percentage = calculate_conversion_percentage(
                manager['new_customers_count'], manager['manager_total']
            )

            # KPI баллы для детализации
            manager_total_points = (manager['manager_quote_points'] or 0) + (manager['manager_completion_points'] or 0)
            manager_avg_points = (
                manager_total_points / manager['manager_total']
                if manager['manager_total'] > 0 else 0.0
            )

            # Format with nested sales_manager object and rounded points
            first_name = manager.get('sales_manager__first_name', '') or ''
            last_name = manager.get('sales_manager__last_name', '') or ''
            full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else manager['sales_manager__username']

            formatted_manager = {
                'sales_manager': {
                    'id': manager['sales_manager_id'],
                    'name': full_name,
                    'username': manager['sales_manager__username'],
                    'email': manager['sales_manager__email'],
                },
                'manager_total': manager['manager_total'],
                'manager_success': manager['manager_success'],
                'manager_pending': manager['manager_pending'],
                'manager_quoted': manager['manager_quoted'],
                'manager_failed': manager['manager_failed'],
                'manager_new_customers': manager['new_customers_count'],

                # Процентные метрики
                'response_time_percentage': round(quote_performance_percentage, 1),
                'follow_up_percentage': round(completion_performance_percentage, 1),
                'conversion_rate': round(conversion_rate, 1),
                'new_customers_percentage': round(new_customers_percentage, 1),

                # KPI баллы для детализации
                'manager_quote_points': round(manager['manager_quote_points'] or 0, 2),
                'manager_completion_points': round(manager['manager_completion_points'] or 0, 2),
                'manager_total_points': round(manager_total_points, 2),
                'manager_avg_points': round(manager_avg_points, 2),
            }
            formatted_performance.append(formatted_manager)

        # Import services to get current weights and calculate weighted scores
        from .services import KPIWeightsServices

        # Restructure to new response format
        restructured_data = []
        for manager_data in formatted_performance:
            # Calculate weighted KPI score using current weights
            weighted_kpi_score = KPIWeightsServices.calculate_weighted_kpi_score(
                response_time_percentage=manager_data['response_time_percentage'],
                follow_up_percentage=manager_data['follow_up_percentage'],
                conversion_rate=manager_data['conversion_rate'],
                new_customer_percentage=manager_data['new_customers_percentage']
            )

            restructured_manager = {
                "manager": {
                    "username": manager_data['sales_manager']['username'],
                    "id": manager_data['sales_manager']['id'],
                    "first_name": manager_data['sales_manager']['name'].split()[0] if ' ' in manager_data['sales_manager']['name'] else manager_data['sales_manager']['name'],
                    "last_name": manager_data['sales_manager']['name'].split()[1] if ' ' in manager_data['sales_manager']['name'] else ""
                },
                "inquiries": {
                    "total": manager_data['manager_total'],
                    "pending": manager_data['manager_pending'],
                    "quoted": manager_data['manager_quoted'],
                    "failed": manager_data['manager_failed'],
                    "success": manager_data['manager_success']
                },
                "kpi": {
                    "response_time": f"{manager_data['response_time_percentage']}",
                    "follow_up": f"{manager_data['follow_up_percentage']}",
                    "conversion_rate": f"{manager_data['conversion_rate']}",
                    "new_customer": f"{manager_data['new_customers_percentage']}",
                    "overall_performance": f"{weighted_kpi_score}"
                }
            }
            restructured_data.append(restructured_manager)

        # Sort by weighted KPI score for better ranking
        restructured_data.sort(key=lambda x: float(x['kpi']['overall_performance']), reverse=True)

        return restructured_data

    @staticmethod
    def get_historical_kpi_trends(
        *, months_back: int = 12,
        manager_id: int = None
    ) -> dict[str, Any]:
        """
        Get historical KPI trends for performance analysis

        Args:
            months_back: Number of months to look back (default: 12)
            manager_id: Optional manager ID to filter by specific manager

        Returns:
            Dictionary with monthly trend data
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months_back * 30)  # Approximate months

        qs = Inquiry.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )

        if manager_id:
            qs = qs.filter(sales_manager_id=manager_id)

        # Group by month and calculate monthly metrics
        monthly_data = qs.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_inquiries=Count('id'),
            success_inquiries=Count(Case(When(status='success', then=1), output_field=IntegerField())),
            failed_inquiries=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            new_customers=Count(Case(When(is_new_customer=True, then=1), output_field=IntegerField())),

            # KPI Grades
            quote_grade_a=Count(Case(When(quote_grade='A', then=1), output_field=IntegerField())),
            quote_grade_b=Count(Case(When(quote_grade='B', then=1), output_field=IntegerField())),
            quote_grade_c=Count(Case(When(quote_grade='C', then=1), output_field=IntegerField())),

            completion_grade_a=Count(Case(When(completion_grade='A', then=1), output_field=IntegerField())),
            completion_grade_b=Count(Case(When(completion_grade='B', then=1), output_field=IntegerField())),
            completion_grade_c=Count(Case(When(completion_grade='C', then=1), output_field=IntegerField())),

            # Monthly KPI Points
            monthly_quote_points=Sum(
                Case(
                    When(quote_grade='A', then=Value(3)),
                    When(quote_grade='B', then=Value(2)),
                    When(quote_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
            monthly_completion_points=Sum(
                Case(
                    When(completion_grade='A', then=Value(3)),
                    When(completion_grade='B', then=Value(2)),
                    When(completion_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
        ).order_by('month')

        # Process monthly data to add calculated fields
        processed_monthly_data = []
        for month_data in monthly_data:
            # Calculate conversion rates and percentages
            month_data['conversion_rate'] = calculate_conversion_percentage(
                month_data['success_inquiries'], month_data['total_inquiries']
            )
            month_data['lead_generation_rate'] = calculate_conversion_percentage(
                month_data['new_customers'], month_data['total_inquiries']
            )

            # Calculate average points
            month_data['total_kpi_points'] = (
                (month_data['monthly_quote_points'] or 0) +
                (month_data['monthly_completion_points'] or 0)
            )

            if month_data['total_inquiries'] > 0:
                month_data['avg_kpi_points'] = month_data['total_kpi_points'] / month_data['total_inquiries']
            else:
                month_data['avg_kpi_points'] = 0.0

            # Calculate grade percentages
            total_graded = month_data['quote_grade_a'] + month_data['quote_grade_b'] + month_data['quote_grade_c']
            if total_graded > 0:
                month_data['quote_a_percentage'] = (month_data['quote_grade_a'] / total_graded) * 100
                month_data['quote_b_percentage'] = (month_data['quote_grade_b'] / total_graded) * 100
                month_data['quote_c_percentage'] = (month_data['quote_grade_c'] / total_graded) * 100
            else:
                month_data['quote_a_percentage'] = month_data['quote_b_percentage'] = month_data['quote_c_percentage'] = 0.0

            processed_monthly_data.append(month_data)

        return {
            'months_back': months_back,
            'start_date': start_date,
            'end_date': end_date,
            'manager_id': manager_id,
            'monthly_trends': processed_monthly_data
        }

    @staticmethod
    def get_team_kpi_comparison(
        *, date_from: datetime = None, date_to: datetime = None,
        min_inquiries: int = 5
    ) -> dict[str, Any]:
        """
        Get team KPI comparison for performance benchmarking

        Args:
            date_from: Optional start date filter
            date_to: Optional end date filter
            min_inquiries: Minimum inquiries required to be included in comparison

        Returns:
            Dictionary with team comparison metrics
        """
        qs = Inquiry.objects.filter(sales_manager__isnull=False)

        # Apply date filters if provided
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        # Get detailed manager statistics
        manager_stats = qs.values(
            'sales_manager_id',
            'sales_manager__username',
            'sales_manager__email'
        ).annotate(
            total_inquiries=Count('id'),
            success_count=Count(Case(When(status='success', then=1), output_field=IntegerField())),
            failed_count=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            new_customers=Count(Case(When(is_new_customer=True, then=1), output_field=IntegerField())),

            # Quote performance
            quote_a_count=Count(Case(When(quote_grade='A', then=1), output_field=IntegerField())),
            quote_b_count=Count(Case(When(quote_grade='B', then=1), output_field=IntegerField())),
            quote_c_count=Count(Case(When(quote_grade='C', then=1), output_field=IntegerField())),

            # Completion performance
            completion_a_count=Count(Case(When(completion_grade='A', then=1), output_field=IntegerField())),
            completion_b_count=Count(Case(When(completion_grade='B', then=1), output_field=IntegerField())),
            completion_c_count=Count(Case(When(completion_grade='C', then=1), output_field=IntegerField())),

            # KPI Points
            total_quote_points=Sum(
                Case(
                    When(quote_grade='A', then=Value(3)),
                    When(quote_grade='B', then=Value(2)),
                    When(quote_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
            total_completion_points=Sum(
                Case(
                    When(completion_grade='A', then=Value(3)),
                    When(completion_grade='B', then=Value(2)),
                    When(completion_grade='C', then=Value(-1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),
        ).filter(
            total_inquiries__gte=min_inquiries
        ).order_by('-total_inquiries')

        # Process and enhance manager data
        enhanced_stats = []
        for manager in manager_stats:
            # Calculate derived metrics
            manager['conversion_rate'] = calculate_conversion_percentage(
                manager['success_count'], manager['total_inquiries']
            )
            manager['lead_generation_rate'] = calculate_conversion_percentage(
                manager['new_customers'], manager['total_inquiries']
            )

            # Total KPI points
            manager['total_kpi_points'] = (
                (manager['total_quote_points'] or 0) +
                (manager['total_completion_points'] or 0)
            )
            manager['avg_kpi_points'] = (
                manager['total_kpi_points'] / manager['total_inquiries']
                if manager['total_inquiries'] > 0 else 0.0
            )

            # Quote grade distribution
            total_quotes = manager['quote_a_count'] + manager['quote_b_count'] + manager['quote_c_count']
            if total_quotes > 0:
                manager['quote_a_rate'] = (manager['quote_a_count'] / total_quotes) * 100
                manager['quote_b_rate'] = (manager['quote_b_count'] / total_quotes) * 100
                manager['quote_c_rate'] = (manager['quote_c_count'] / total_quotes) * 100
            else:
                manager['quote_a_rate'] = manager['quote_b_rate'] = manager['quote_c_rate'] = 0.0

            # Completion grade distribution
            total_completions = manager['completion_a_count'] + manager['completion_b_count'] + manager['completion_c_count']
            if total_completions > 0:
                manager['completion_a_rate'] = (manager['completion_a_count'] / total_completions) * 100
                manager['completion_b_rate'] = (manager['completion_b_count'] / total_completions) * 100
                manager['completion_c_rate'] = (manager['completion_c_count'] / total_completions) * 100
            else:
                manager['completion_a_rate'] = manager['completion_b_rate'] = manager['completion_c_rate'] = 0.0

            enhanced_stats.append(manager)

        # Calculate team averages for benchmarking
        if enhanced_stats:
            team_avg_conversion = sum(m['conversion_rate'] for m in enhanced_stats) / len(enhanced_stats)
            team_avg_lead_gen = sum(m['lead_generation_rate'] for m in enhanced_stats) / len(enhanced_stats)
            team_avg_kpi_points = sum(m['avg_kpi_points'] for m in enhanced_stats) / len(enhanced_stats)
            team_avg_quote_a = sum(m['quote_a_rate'] for m in enhanced_stats) / len(enhanced_stats)
            team_avg_completion_a = sum(m['completion_a_rate'] for m in enhanced_stats) / len(enhanced_stats)
        else:
            team_avg_conversion = team_avg_lead_gen = team_avg_kpi_points = 0.0
            team_avg_quote_a = team_avg_completion_a = 0.0

        # Rank managers by different metrics
        conversion_ranking = sorted(enhanced_stats, key=lambda x: x['conversion_rate'], reverse=True)
        kpi_points_ranking = sorted(enhanced_stats, key=lambda x: x['avg_kpi_points'], reverse=True)
        quote_performance_ranking = sorted(enhanced_stats, key=lambda x: x['quote_a_rate'], reverse=True)

        return {
            'team_statistics': enhanced_stats,
            'team_averages': {
                'avg_conversion_rate': team_avg_conversion,
                'avg_lead_generation_rate': team_avg_lead_gen,
                'avg_kpi_points': team_avg_kpi_points,
                'avg_quote_a_rate': team_avg_quote_a,
                'avg_completion_a_rate': team_avg_completion_a,
            },
            'rankings': {
                'by_conversion_rate': conversion_ranking[:5],  # Top 5
                'by_kpi_points': kpi_points_ranking[:5],  # Top 5
                'by_quote_performance': quote_performance_ranking[:5],  # Top 5
            },
            'filters': {
                'date_from': date_from,
                'date_to': date_to,
                'min_inquiries': min_inquiries,
                'total_managers': len(enhanced_stats)
            }
        }
