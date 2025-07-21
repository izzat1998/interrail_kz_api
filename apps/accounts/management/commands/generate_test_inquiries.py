"""
Django management command to generate test inquiries for development and testing.
Usage: python manage.py generate_test_inquiries --count 50
"""

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.inquiries.models import Inquiry

User = get_user_model()


class Command(BaseCommand):
    help = "Generate test inquiries for development and testing purposes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of inquiries to generate (default: 10)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing inquiries before generating new ones",
        )

    def handle(self, *args, **options):
        count = options["count"]
        clear_existing = options["clear"]

        if count <= 0:
            raise CommandError("Count must be greater than 0")

        if clear_existing:
            deleted_count = Inquiry.objects.count()
            Inquiry.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} existing inquiries")
            )

        # Get available sales managers (manager and admin users)
        sales_managers = list(
            User.objects.filter(user_type__in=["manager", "admin"], is_active=True)
        )

        if not sales_managers:
            raise CommandError(
                "No sales managers found. Create manager or admin users first:\n"
                "python manage.py createsuperuser\n"
                "or create manager users through the admin panel."
            )

        # Sample data for generating realistic inquiries
        clients = [
            "Kazakhstan Railways",
            "Nur-Sultan Transport",
            "Almaty Metro Group",
            "Interrail Kazakhstan",
            "Trans-Asia Express",
            "Silk Road Logistics",
            "Central Asian Rail",
            "Astana Transit Corp",
            "Golden Eagle Rail",
            "Nomad Express",
            "Steppe Railway Co",
            "Eurasian Rail Solutions",
            "Kazakhstan Freight",
            "Turkestan Railway",
            "Caspian Rail Group",
        ]

        inquiry_texts = [
            "We need a comprehensive rail transport solution for cargo delivery between Almaty and Nur-Sultan. The cargo includes industrial equipment and we require special handling procedures.",
            "Looking for passenger rail services connecting major cities in Kazakhstan. We represent a tourism company and need regular service for our clients.",
            "Our company requires freight rail transportation for agricultural products from southern regions to processing facilities in the north.",
            "We need express passenger services with premium amenities for business travelers. Route should cover Almaty, Shymkent, and Nur-Sultan.",
            "Seeking rail cargo services for mining equipment transportation. Heavy machinery needs to be moved from port facilities to mining sites.",
            "Our logistics company needs regular freight services for container transportation along the New Silk Road corridor.",
            "We require specialized rail cars for petroleum product transportation with all necessary safety certifications and protocols.",
            "Looking for high-speed passenger rail connections for daily commuters between major urban centers.",
            "Our manufacturing company needs reliable freight services for raw material delivery and finished product distribution.",
            "We need rail transportation for grain exports with proper storage and handling facilities at terminals.",
            "Seeking luxury passenger rail services for international tourists visiting Kazakhstan historical sites.",
            "Our company requires temperature-controlled rail cars for food product transportation across the country.",
            "We need freight rail services for construction materials delivery to major infrastructure projects.",
            "Looking for passenger rail services with accessibility features for elderly and disabled travelers.",
            "Our energy company needs specialized rail transportation for wind turbine components to renewable energy sites.",
        ]

        comments = [
            "Initial inquiry received. Waiting for detailed requirements.",
            "Customer provided additional specifications. Preparing quotation.",
            "Quote sent to customer. Awaiting approval and contract signing.",
            "Contract signed. Service implementation in progress.",
            "Service completed successfully. Customer satisfaction confirmed.",
            "Additional requirements discussed. Quote under revision.",
            "Technical feasibility study completed. Awaiting management approval.",
            "Customer requested service modifications. Updating proposal.",
            "Logistics planning completed. Ready for service execution.",
            "Special equipment requirements identified. Sourcing in progress.",
            "",  # Some inquiries might not have comments
        ]

        statuses = ["pending", "quoted", "success", "failed"]

        created_inquiries = []

        for _ in range(count):
            # Random data selection
            client = random.choice(clients)
            text = random.choice(inquiry_texts)
            comment = random.choice(comments)
            status = random.choice(statuses)
            is_new_customer = random.choice([True, False])

            # Assign sales manager (all inquiries must have a manager)
            sales_manager = random.choice(sales_managers)

            inquiry = Inquiry.objects.create(
                client=client,
                text=text,
                comment=comment,
                status=status,
                is_new_customer=is_new_customer,
                sales_manager=sales_manager,
            )
            created_inquiries.append(inquiry)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(created_inquiries)} test inquiries"
            )
        )

        # Summary statistics
        status_counts = {}
        for status, _ in Inquiry.STATUS_CHOICES:
            status_counts[status] = len(
                [i for i in created_inquiries if i.status == status]
            )

        self.stdout.write("\nSummary:")
        for status, count in status_counts.items():
            self.stdout.write(f"  {status.title()}: {count} inquiries")

        new_customer_count = len([i for i in created_inquiries if i.is_new_customer])
        self.stdout.write(f"  New customers: {new_customer_count} inquiries")

        manager_distribution = {}
        for inquiry in created_inquiries:
            manager_name = inquiry.sales_manager.username
            manager_distribution[manager_name] = (
                manager_distribution.get(manager_name, 0) + 1
            )

        self.stdout.write(f"  Assigned to {len(sales_managers)} managers:")
        for manager, count in manager_distribution.items():
            self.stdout.write(f"    {manager}: {count} inquiries")
