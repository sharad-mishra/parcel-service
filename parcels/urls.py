from django.urls import path
from .views import (
    CreateParcelView,
    ParcelDetailView,
    ListUserParcelsView,
    UpdateParcelStatusView,
    HealthCheckView,

)

urlpatterns = [
    path('create/', CreateParcelView.as_view(), name='create-parcel'),
    path('<uuid:pk>/', ParcelDetailView.as_view(), name='parcel-detail'),
    path('my/', ListUserParcelsView.as_view(), name='my-parcels'),
    path('<uuid:pk>/status/', UpdateParcelStatusView.as_view(), name='update-status'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
]
