import os
import sys
import django
import uuid

# Add the project root (the parent of `config/`) to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from parcels.models import Parcel

def generate_tracking_id():
    return str(uuid.uuid4())[:12].upper()

def backfill():
    parcels = Parcel.objects.filter(tracking_id__isnull=True)
    print(f"Found {parcels.count()} parcels without tracking_id")

    for parcel in parcels:
        parcel.tracking_id = generate_tracking_id()
        parcel.save()
        print(f"Assigned tracking ID to parcel {parcel.id}")

if __name__ == "__main__":
    backfill()
