"""
Tests for Payment Service Escrow Manager.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.services.escrow_manager import release_trip_escrow, refund_trip_escrow
from app.models.models import Payment

class MockSession:
    def __init__(self, payments):
        self.payments = payments
        self.committed = False

    async def execute(self, stmt):
        class MockResult:
            def __init__(self, items):
                self.items = items
            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self.items = items
                    def all(self):
                        return self.items
                return MockScalars(self.items)
        
        # Simple mock filtering for `where(Payment.status == "held")` and `trip_id == ...`
        held = [p for p in self.payments if p.status == "held"]
        return MockResult(held)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_release_trip_escrow():
    trip_id = uuid.uuid4()
    
    payments = [
        Payment(
            id=uuid.uuid4(),
            trip_id=trip_id,
            amount=15000,
            gateway="stripe",
            gateway_payment_id="pi_mock1",
            status="held"
        ),
        Payment(
            id=uuid.uuid4(),
            trip_id=trip_id,
            amount=20000,
            gateway="razorpay",
            gateway_payment_id="order_mock1",
            gateway_transfer_id="trf_mock1",
            status="held"
        ),
        Payment(
            id=uuid.uuid4(),
            trip_id=trip_id,
            amount=5000,
            gateway="stripe",
            gateway_payment_id="pi_mock2",
            status="pending"  # Should not be processed
        )
    ]
    
    session = MockSession(payments)
    
    with patch('app.services.stripe_gateway.capture_payment', new_callable=AsyncMock) as mock_stripe_capture, \
         patch('app.services.razorpay_gateway.release_escrow', new_callable=AsyncMock) as mock_razorpay_release:
        
        mock_stripe_capture.return_value = True
        mock_razorpay_release.return_value = True
        
        result = await release_trip_escrow(session, trip_id)
        
        assert session.committed is True
        assert result.total_released == 35000
        assert result.payments_released == 2
        
        assert payments[0].status == "released"
        assert payments[1].status == "released"
        assert payments[2].status == "pending"  # unchanged
        
        mock_stripe_capture.assert_called_once_with("pi_mock1")
        mock_razorpay_release.assert_called_once_with("order_mock1", "trf_mock1")


@pytest.mark.asyncio
async def test_refund_trip_escrow():
    trip_id = uuid.uuid4()
    
    payments = [
        Payment(
            id=uuid.uuid4(),
            trip_id=trip_id,
            amount=15000,
            gateway="stripe",
            gateway_payment_id="pi_mock1",
            status="held"
        )
    ]
    
    session = MockSession(payments)
    
    with patch('app.services.stripe_gateway.refund_payment', new_callable=AsyncMock) as mock_stripe_refund:
        mock_stripe_refund.return_value = True
        
        result = await refund_trip_escrow(session, trip_id)
        
        assert session.committed is True
        assert result.total_refunded == 15000
        assert result.payments_refunded == 1
        
        assert payments[0].status == "refunded"
        mock_stripe_refund.assert_called_once_with("pi_mock1")
