from django.contrib import admin
from django.utils.html import format_html

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "client",
        "colored_status",
        "attachment_display",
        "sales_manager",
        "is_new_customer",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "status",
        "is_new_customer",
        "created_at",
        "updated_at",
        "sales_manager__user_type",
    ]
    search_fields = [
        "client",
        "text",
        "comment",
        "sales_manager__username",
        "sales_manager__email",
    ]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 25
    ordering = ["-created_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("client", "text", "attachment", "comment")}),
        (
            "Status & Assignment",
            {"fields": ("status", "sales_manager", "is_new_customer")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def colored_status(self, obj):
        colors = {
            "pending": "orange",
            "quoted": "blue",
            "success": "green",
            "failed": "red",
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, "black"),
            obj.get_status_display(),
        )

    colored_status.short_description = "Status"

    def attachment_display(self, obj):
        if obj.attachment:
            return format_html(
                '<a href="{}" target="_blank">📎 View</a>',
                obj.attachment.url
            )
        return "-"

    attachment_display.short_description = "Attachment"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sales_manager")
