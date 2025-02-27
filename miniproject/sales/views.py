from django.shortcuts import render

# Create your views here.
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db import transaction

from utils.pdf_utils import pdf_response, render_pdf

from .models import Invoice, SalesOrder
from .serializers import InvoiceSerializer, SalesOrderSerializer

User = get_user_model()

class SalesOrderListCreateView(generics.ListCreateAPIView):
    """
    GET: List all Sales Orders (Admins & Sales see all, customers see only theirs).
    POST: Create a new Sales Order (customers can create for themselves).
    """
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer']
    search_fields = ['id', 'customer__username']
    ordering_fields = ['created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        if user.role in ["admin", "sales"] or user.is_staff:
            return SalesOrder.objects.all()
        # Customers see only their own orders.
        return SalesOrder.objects.filter(customer=user)

    def create(self, request, *args, **kwargs):
        # Ensure the customer is set to the logged-in user.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Using perform_create with explicit customer assignment
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

class SalesOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a Sales Order.
    PUT/PATCH: Update the order (only Admin/Sales can change status; customers limited to pending orders).
    DELETE: Cancel or delete the order (Admin/Sales only).
    """
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ["admin", "sales"] or user.is_staff:
            return SalesOrder.objects.all()
        return SalesOrder.objects.filter(customer=user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        user = request.user
        data = request.data.copy()

        # Prevent customers from updating status to approved/completed.
        if user.role not in ["admin", "sales"] and "status" in data:
            if data["status"] in ["approved", "completed"]:
                raise PermissionDenied("Not allowed to approve/complete orders.")

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

class InvoiceCreateView(generics.CreateAPIView):
    """
    Create an invoice for a SalesOrder.
    Only Admin or Sales can generate an invoice once the order is approved.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        order_id = self.request.data.get("sales_order")
        sales_order = get_object_or_404(SalesOrder, id=order_id)

        # Only Admin or Sales may create invoices.
        if user.role not in ["admin", "sales"] and not user.is_staff:
            raise PermissionDenied("You do not have permission to create invoices.")

        # Only allow invoice creation if the order is approved.
        if sales_order.status != "approved":
            raise ValidationError("Cannot generate invoice for a non-approved order.")

        # Prevent duplicate invoices.
        if hasattr(sales_order, "invoice"):
            raise ValidationError("Invoice already exists for this order.")

        serializer.save(sales_order=sales_order)

class InvoiceRetrievePDFView(generics.RetrieveAPIView):
    """
    Retrieve an invoice as a PDF download.
    Access is limited: Admin/Sales can retrieve any, while customers can only access their own.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ["admin", "sales"] or user.is_staff:
            return Invoice.objects.all()
        # Customers may only access invoices for their orders.
        return Invoice.objects.filter(sales_order__customer=user)

    def retrieve(self, request, *args, **kwargs):
        invoice = self.get_object()
        sales_order = invoice.sales_order
        context = {
            "invoice": invoice,
            "sales_order": sales_order,
            "items": sales_order.items.all(),
            "customer": sales_order.customer,
            "total": sales_order.total,
            "date": timezone.now(),
        }
        # Render PDF using a dedicated template.
        pdf_content = render_pdf("invoice_template.html", context_dict=context)
        return pdf_response(pdf_content, filename=f"invoice_{invoice.id}.pdf")
