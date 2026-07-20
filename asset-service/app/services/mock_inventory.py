"""
Mock Inventory Adapter for Slice.
Simulates fetching luxury assets (villas, yachts) from an external travel API.
"""

import uuid
from typing import List
from maci_core.schemas.asset import AssetCreate

def generate_mock_luxury_assets() -> List[AssetCreate]:
    return [
        AssetCreate(
            title="Cliffside Mansion in Bali",
            description="A breathtaking 6-bedroom villa overlooking the ocean. Includes private chef and infinity pool.",
            asset_type="villa",
            location="Uluwatu, Bali, Indonesia",
            total_price=1200.0,
            currency="USD",
            total_slices=6,
            external_reference_id="mock_expedia_bali_123",
            media_urls=["https://example.com/bali1.jpg", "https://example.com/bali2.jpg"]
        ),
        AssetCreate(
            title="Chartered Catamaran in Greece",
            description="Sail the Aegean Sea in a luxury 4-cabin catamaran. Includes a skipper and daily meals.",
            asset_type="yacht",
            location="Mykonos, Greece",
            total_price=2400.0,
            currency="USD",
            total_slices=4,
            external_reference_id="mock_amadeus_greece_456",
            media_urls=["https://example.com/yacht1.jpg"]
        ),
        AssetCreate(
            title="Penthouse Suite in Dubai",
            description="Ultra-luxury penthouse with Burj Khalifa views. Access to private VIP lounge.",
            asset_type="penthouse",
            location="Downtown Dubai, UAE",
            total_price=3000.0,
            currency="USD",
            total_slices=10,
            external_reference_id="mock_booking_dubai_789",
            media_urls=["https://example.com/dubai1.jpg"]
        )
    ]
