from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api_config.pagination import (
    CustomPageNumberPagination,
    get_paginated_response,
)
from apps.api_config.utils import inline_serializer
from apps.authentication.authentication import CookieJWTAuthentication
from apps.core.permissions import IsAdminOnly, IsManagerOrAdmin

from .models import Inquiry
from .selectors import InquirySelectors
from .services import InquiryServices


class AttachmentField(serializers.Field):
    """Custom field that handles both file uploads and string commands"""

    def to_internal_value(self, data):
        # Handle file uploads (multipart requests)
        if hasattr(data, 'read'):
            return data

        # Handle string commands (JSON requests)
        if isinstance(data, str):
            if data == 'DELETE':
                return None  # Signal for deletion
            elif data == '':
                return ...  # Signal for no change (ellipsis)
            else:
                raise serializers.ValidationError(
                    "Invalid value. Use 'DELETE' to remove attachment or upload a file."
                )

        raise serializers.ValidationError(
            "Must be a file or 'DELETE' string."
        )

    def to_representation(self, value):
        if hasattr(value, 'url'):
            return value.url
        return str(value) if value else None


class InquiryListApiView(APIView):
    """
    List inquiries
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsManagerOrAdmin]

    class Pagination(CustomPageNumberPagination):
        page_size = 10
        max_page_size = 50

    class FilterSerializer(serializers.Serializer):
        status = serializers.ListField(
            child=serializers.ChoiceField(choices=Inquiry.STATUS_CHOICES),
            required=False,
            allow_empty=True,
        )

        text = serializers.CharField(required=False)
        comment = serializers.CharField(required=False)
        search = serializers.CharField(required=False)
        is_new_customer = serializers.CharField(required=False)
        sales_manager_id = serializers.IntegerField(required=False)

    class InquiryListOutputSerializer(serializers.ModelSerializer):
        attachment_url = serializers.SerializerMethodField()
        attachment_name = serializers.SerializerMethodField()
        has_attachment = serializers.SerializerMethodField()
        status_display = serializers.CharField(source='get_status_display', read_only=True)
        sales_manager = inline_serializer(
            fields={
                "id": serializers.IntegerField(read_only=True),
                "username": serializers.CharField(read_only=True),
                "email": serializers.EmailField(read_only=True),
            },
            allow_null=True,
        )

        class Meta:
            model = Inquiry
            fields = [
                'id', 'client', 'text', 'attachment_url', 'attachment_name',
                'has_attachment', 'status', 'status_display', 'sales_manager',
                'is_new_customer', 'created_at', 'updated_at'
            ]

        def get_attachment_url(self, obj):
            return obj.attachment.url if obj.attachment else None

        def get_attachment_name(self, obj):
            return obj.attachment.name.split('/')[-1] if obj.attachment else None

        def get_has_attachment(self, obj):
            return bool(obj.attachment)

    @extend_schema(
        tags=["Inquiries"],
        summary="List Inquiries",
        parameters=[
            OpenApiParameter(
                "page", OpenApiTypes.INT, description="Page number (default: 1)"
            ),
            OpenApiParameter(
                "page_size",
                OpenApiTypes.INT,
                description="Items per page (default: 10, max: 100)",
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                description="Filter by multiple statuses (comma-separated)",
            ),
            OpenApiParameter(
                "search",
                OpenApiTypes.STR,
                description="Search in client, text, comment",
            ),
            OpenApiParameter(
                "is_new_customer",
                OpenApiTypes.BOOL,
                description="Filter by new customer status",
            ),
            OpenApiParameter(
                "sales_manager_id",
                OpenApiTypes.INT,
                description="Filter by sales manager ID",
            ),
        ],
        responses={200: InquiryListOutputSerializer},
    )
    def get(self, request):
        # Validate filters
        status_list = request.GET.getlist("status[]")

        # Build data dict for serializer (preserve single values)
        data = {}
        for key, value in request.query_params.items():
            if key != "status[]":  # Handle status[] separately
                data[key] = value

        if status_list:
            data["status"] = status_list

        filter_serializer = self.FilterSerializer(data=data)
        filter_serializer.is_valid(raise_exception=True)

        queryset = InquirySelectors.get_inquiries_list(
            filters=filter_serializer.validated_data
        )

        # Use pagination helper
        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.InquiryListOutputSerializer,
            queryset=queryset,
            request=request,
            view=self,
        )


class InquiryCreateApiView(APIView):
    """
    Create inquiry
    Supports both JSON (text) and multipart/form-data (file) requests
    """

    # authentication_classes = [CookieJWTAuthentication]
    # permission_classes = [IsManagerOrAdmin]
    parser_classes = [JSONParser, MultiPartParser]

    class InquiryCreateSerializer(serializers.Serializer):
        client = serializers.CharField(max_length=255, required=True)
        text = serializers.CharField(required=False, allow_blank=True)
        attachment = serializers.FileField(required=False, allow_null=True)
        status = serializers.ChoiceField(
            choices=Inquiry.STATUS_CHOICES,
            default=Inquiry.STATUS_CHOICES[0][0],
        )
        comment = serializers.CharField(required=False, allow_blank=True)
        sales_manager_id = serializers.IntegerField(required=True)
        is_new_customer = serializers.BooleanField(default=False)



    class InquiryCreateOutputSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        client = serializers.CharField(read_only=True)
        text = serializers.CharField(read_only=True, allow_null=True)
        attachment_url = serializers.CharField(read_only=True, allow_null=True)
        attachment_name = serializers.CharField(read_only=True, allow_null=True)
        has_attachment = serializers.BooleanField(read_only=True)
        status = serializers.CharField(read_only=True)
        status_display = serializers.CharField(read_only=True)
        sales_manager = inline_serializer(
            fields={
                "id": serializers.IntegerField(read_only=True),
                "username": serializers.CharField(read_only=True),
                "email": serializers.EmailField(read_only=True),
            },
            allow_null=True,
        )
        is_new_customer = serializers.BooleanField(read_only=True)
        comment = serializers.CharField(read_only=True, allow_blank=True)
        created_at = serializers.DateTimeField(read_only=True)
        updated_at = serializers.DateTimeField(read_only=True)

    @extend_schema(
        tags=["Inquiries"],
        summary="Create Inquiry",
        request=InquiryCreateSerializer,
        responses={201: InquiryCreateOutputSerializer},
    )
    def post(self, request):
        serializer = self.InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            inquiry = InquiryServices.create_inquiry(
                client=serializer.validated_data["client"],
                text=serializer.validated_data.get("text"),
                attachment=serializer.validated_data.get("attachment"),
                comment=serializer.validated_data.get("comment", ""),
                sales_manager_id=serializer.validated_data.get("sales_manager_id"),
                is_new_customer=serializer.validated_data.get("is_new_customer", False),
                status=serializer.validated_data.get("status", "pending"),
            )

            data = InquirySelectors.get_inquiry_by_id(inquiry_id=inquiry.id)

            return Response(
                self.InquiryCreateOutputSerializer(data).data,
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InquiryDetailApiView(APIView):
    """
    Retrieve inquiry detail
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsManagerOrAdmin]

    class InquiryDetailSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        client = serializers.CharField(read_only=True)
        text = serializers.CharField(read_only=True, allow_null=True)
        attachment_url = serializers.CharField(read_only=True, allow_null=True)
        attachment_name = serializers.CharField(read_only=True, allow_null=True)
        has_attachment = serializers.BooleanField(read_only=True)
        status = serializers.CharField(read_only=True)
        status_display = serializers.CharField(read_only=True)
        sales_manager = inline_serializer(
            fields={
                "id": serializers.IntegerField(read_only=True),
                "username": serializers.CharField(read_only=True),
                "email": serializers.EmailField(read_only=True),
            },
            allow_null=True,
        )
        is_new_customer = serializers.BooleanField(read_only=True)
        comment = serializers.CharField(read_only=True, allow_blank=True)
        created_at = serializers.DateTimeField(read_only=True)
        updated_at = serializers.DateTimeField(read_only=True)

    @extend_schema(
        tags=["Inquiries"],
        summary="Get Inquiry Detail",
        responses={200: InquiryDetailSerializer},
    )
    def get(self, request, inquiry_id):
        try:
            data = InquirySelectors.get_inquiry_by_id(inquiry_id=inquiry_id)

            return Response(
                self.InquiryDetailSerializer(data).data, status=status.HTTP_200_OK
            )
        except Inquiry.DoesNotExist:
            return Response(
                {"message": "Inquiry not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InquiryUpdateApiView(APIView):
    """
    Update inquiry
    Supports switching between text and file
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsManagerOrAdmin]
    parser_classes = [JSONParser, MultiPartParser]

    class InquiryUpdateSerializer(serializers.Serializer):
        client = serializers.CharField(max_length=255, required=False)
        text = serializers.CharField(required=False, allow_blank=True)
        attachment = AttachmentField(required=False)
        status = serializers.ChoiceField(choices=Inquiry.STATUS_CHOICES, required=False)
        comment = serializers.CharField(required=False, allow_blank=True)
        sales_manager_id = serializers.IntegerField(required=False)
        is_new_customer = serializers.BooleanField(required=False)

        def validate(self, data):
            # Handle attachment field - can be file upload or string command
            if 'attachment' in self.initial_data:
                attachment_value = self.initial_data['attachment']

                # Handle file uploads (multipart requests)
                if hasattr(attachment_value, 'read'):
                    data['attachment'] = attachment_value
                # Handle string commands (JSON requests)
                elif isinstance(attachment_value, str):
                    if attachment_value == 'DELETE':
                        data['attachment'] = None  # Signal for deletion
                    elif attachment_value == '':
                        data.pop('attachment', None)  # Remove from data = no change
                    else:
                        raise serializers.ValidationError(
                            {"attachment": "Invalid value. Use 'DELETE' to remove attachment or upload a file."}
                        )
                else:
                    raise serializers.ValidationError(
                        {"attachment": "Must be a file or 'DELETE' string."}
                    )

            return data




    class InquiryUpdateResponseSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        client = serializers.CharField(read_only=True)
        text = serializers.CharField(read_only=True, allow_null=True)
        attachment_url = serializers.CharField(read_only=True, allow_null=True)
        attachment_name = serializers.CharField(read_only=True, allow_null=True)
        has_attachment = serializers.BooleanField(read_only=True)
        status = serializers.CharField(read_only=True)
        status_display = serializers.CharField(read_only=True)
        sales_manager = inline_serializer(
            fields={
                "id": serializers.IntegerField(read_only=True),
                "username": serializers.CharField(read_only=True),
                "email": serializers.EmailField(read_only=True),
            },
            allow_null=True,
        )
        is_new_customer = serializers.BooleanField(read_only=True)
        comment = serializers.CharField(read_only=True, allow_blank=True)
        created_at = serializers.DateTimeField(read_only=True)
        updated_at = serializers.DateTimeField(read_only=True)

    @extend_schema(
        tags=["Inquiries"],
        summary="Update Inquiry",
        request=InquiryUpdateSerializer,
        responses={200: InquiryUpdateResponseSerializer},
    )
    def put(self, request, inquiry_id):
        serializer = self.InquiryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            inquiry = InquirySelectors.get_inquiry_instance_by_id(inquiry_id=inquiry_id)

            # Prepare update kwargs, only include fields that were provided
            update_kwargs = {
                "inquiry": inquiry,
            }

            # Only include fields that were explicitly provided in the request
            for field in ["client", "text", "status", "comment", "sales_manager_id", "is_new_customer"]:
                if field in serializer.validated_data:
                    update_kwargs[field] = serializer.validated_data[field]

            # Handle attachment separately to distinguish between None and not provided
            if "attachment" in serializer.validated_data:
                update_kwargs["attachment"] = serializer.validated_data["attachment"]

            updated_inquiry = InquiryServices.update_inquiry(**update_kwargs)

            # Get formatted data directly from updated inquiry
            data = InquirySelectors.get_inquiry_by_id(inquiry_id=updated_inquiry.id)
            return Response(
                self.InquiryUpdateResponseSerializer(data).data,
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Inquiry.DoesNotExist:
            return Response(
                {"message": "Inquiry not found"}, status=status.HTTP_404_NOT_FOUND
            )


class InquiryDeleteApiView(APIView):
    """
    Delete inquiry
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOnly]

    class DeleteSuccessSerializer(serializers.Serializer):
        message = serializers.CharField()

    @extend_schema(
        tags=["Inquiries"],
        summary="Delete Inquiry",
        responses={200: DeleteSuccessSerializer},
    )
    def delete(self, request, inquiry_id):
        try:
            inquiry = InquirySelectors.get_inquiry_instance_by_id(inquiry_id=inquiry_id)
            InquiryServices.delete_inquiry(inquiry=inquiry)

            return Response(
                self.DeleteSuccessSerializer(
                    {"message": "Inquiry deleted successfully"}
                ).data,
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Inquiry.DoesNotExist:
            return Response(
                {"message": "Inquiry not found"}, status=status.HTTP_404_NOT_FOUND
            )


class InquiryStatsApiView(APIView):
    """
    Get inquiry statistics
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsManagerOrAdmin]

    class InquiryStatsOutputSerializer(serializers.Serializer):
        total_inquiries = serializers.IntegerField()
        pending_count = serializers.IntegerField()
        quoted_count = serializers.IntegerField()
        success_count = serializers.IntegerField()
        failed_count = serializers.IntegerField()
        new_customers_count = serializers.IntegerField()
        conversion_rate = serializers.FloatField()

    @extend_schema(
        tags=["Inquiries"],
        summary="Get Inquiry Statistics",
        responses={200: InquiryStatsOutputSerializer},
    )
    def get(self, request):
        data = InquirySelectors.get_inquiries_stats()

        return Response(
            self.InquiryStatsOutputSerializer(data).data, status=status.HTTP_200_OK
        )
