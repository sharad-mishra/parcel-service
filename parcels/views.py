import os
import requests
import jwt

from django.conf import settings
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied

from .models import Parcel
from .serializers import ParcelSerializer
from parcels.utils import trigger_email_notification


def decode_jwt_from_request(request):
    token = request.headers.get('Authorization', '').split('Bearer ')[-1]
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise PermissionDenied("Token expired")
    except jwt.DecodeError:
        raise PermissionDenied("Invalid token")


class CreateParcelView(generics.CreateAPIView):
    queryset = Parcel.objects.all()
    serializer_class = ParcelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user_data = decode_jwt_from_request(self.request)
        sender_id = user_data.get("user_id")
        user_email = user_data.get("email")
        user_name = user_email.split('@')[0] if user_email else "User"

        # 1. Assign a driver
        assigned_driver_id, driver_info = self.get_available_driver()

        # 2. Save parcel with driver and sender
        parcel = serializer.save(sender_id=sender_id, assigned_driver_id=assigned_driver_id)

        # 3. Mark driver unavailable
        if assigned_driver_id:
            self.mark_driver_unavailable(assigned_driver_id)

        # 4. Trigger email notifications
        if user_email:
            self.send_notifications(user_email, user_name, parcel, driver_info, assigned_driver_id)
        else:
            print("❌ No user_email found in JWT — skipping email notification.")

        # 5. Trigger payment
        self.trigger_payment(parcel)

    def get_available_driver(self):
        try:
            USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")
            response = requests.get(f"{USER_SERVICE_URL}/api/users/available-driver/")
            if response.status_code == 200:
                driver_data = response.json()
                return driver_data.get("driver_id"), {
                    "driver_name": driver_data.get("driver_name", "Driver"),
                    "driver_contact": driver_data.get("driver_contact", "N/A")
                }
        except Exception as e:
            print("⚠️ Error fetching driver:", e)
        return None, {}

    def mark_driver_unavailable(self, driver_id):
        try:
            USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")
            requests.patch(f"{USER_SERVICE_URL}/api/users/{driver_id}/mark-unavailable/")
        except Exception as e:
            print("⚠️ Error marking driver unavailable:", e)

    def send_notifications(self, to, user_name, parcel, driver_info, assigned_driver_id):
        trigger_email_notification(
            to=to,
            template_type="parcel_created",
            context={
                "user_name": user_name,
                "tracking_id": parcel.tracking_id,
                "pickup_address": parcel.pickup_address,
            }
        )

        if assigned_driver_id:
            trigger_email_notification(
                to=to,
                template_type="driver_assigned",
                context={
                    "user_name": user_name,
                    "tracking_id": parcel.tracking_id,
                    "driver_name": driver_info.get("driver_name"),
                    "driver_contact": driver_info.get("driver_contact")
                }
            )

    def trigger_payment(self, parcel):
        try:
            PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8003")

        # Ensure weight is float (DecimalField from DB needs conversion)
            weight = float(parcel.weight_kg) if parcel.weight_kg is not None else 0.0

            payment_payload = {
                "tracking_id": parcel.tracking_id,
                "method": "upi",  # Can later make this dynamic
                "weight": weight
            }

            response = requests.post(f"{PAYMENT_SERVICE_URL}/api/payments/pay/", json=payment_payload)

            if response.status_code == 201:
                print("✅ Payment successfully processed for parcel:", parcel.tracking_id)
            else:
                print("⚠️ Payment request failed:", response.text)

        except Exception as e:
            print("❌ Payment service error:", e)

class ParcelDetailView(generics.RetrieveAPIView):
    queryset = Parcel.objects.all()
    serializer_class = ParcelSerializer
    permission_classes = [permissions.IsAuthenticated]


class ListUserParcelsView(generics.ListAPIView):
    serializer_class = ParcelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assigned_driver_id']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        user_data = decode_jwt_from_request(self.request)
        return Parcel.objects.filter(sender_id=user_data.get("user_id"))


class UpdateParcelStatusView(generics.UpdateAPIView):
    queryset = Parcel.objects.all()
    serializer_class = ParcelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        parcel = self.get_object()
        user_data = decode_jwt_from_request(request)

        if not (user_data.get("user_id") == parcel.assigned_driver_id or user_data.get("role") == "admin"):
            return Response({'error': 'Permission denied'}, status=403)

        new_status = request.data.get('status')
        if new_status not in dict(Parcel.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=400)

        parcel.status = new_status
        parcel.save()

        if new_status == "delivered" and parcel.assigned_driver_id:
            try:
                requests.patch(
                    f'http://localhost:8001/api/users/{parcel.assigned_driver_id}/mark-available/'
                )
            except Exception as e:
                print("⚠️ Error marking driver available:", e)

        sender_email = user_data.get("email")
        user_name = sender_email.split('@')[0] if sender_email else "User"

        if not sender_email:
            print("❌ No email in JWT — skipping delivery status email.")
            return Response({'message': f'Status updated to {new_status}'}, status=200)

        email_context = {
            "user_name": user_name,
            "tracking_id": parcel.tracking_id
        }

        if new_status == "in_transit":
            email_context["current_location"] = "Distribution Hub"
            trigger_email_notification(
                to=sender_email,
                template_type="parcel_in_transit",
                context=email_context
            )

        elif new_status == "delivered":
            email_context["delivery_time"] = str(parcel.updated_at)
            trigger_email_notification(
                to=sender_email,
                template_type="parcel_delivered",
                context=email_context
            )

        elif new_status == "cancelled":
            email_context["cancellation_reason"] = request.data.get("reason", "Not specified")
            trigger_email_notification(
                to=sender_email,
                template_type="parcel_cancelled",
                context=email_context
            )

        return Response({'message': f'Status updated to {new_status}'}, status=200)


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok"})

