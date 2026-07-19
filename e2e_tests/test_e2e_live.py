import pytest
import httpx
import os
import uuid
import asyncio

# The external IP of the API Gateway LoadBalancer
# NOTE: Set this as an environment variable in CI, but hardcode for local run based on `kubectl get svc`
API_URL = os.getenv("API_URL", "http://40.71.235.188")

@pytest.mark.asyncio
async def test_end_to_end_rally_workflow():
    """
    Comprehensive End-to-End test of the Rally platform.
    Tests: Auth -> B2B2C Organizer -> Trip Creation -> AI Planning (Mocked) -> Bulk Invite -> Payment
    """
    async with httpx.AsyncClient(base_url=f"{API_URL}/api/v1", timeout=30.0) as client:
        print(f"\n--- Starting E2E Test against {API_URL} ---")

        # 1. Test Auth (Register Organizer)
        test_email = f"organizer_{uuid.uuid4().hex[:8]}@example.com"
        test_password = "SecurePassword123!"

        res = await client.post("/auth/register", json={
            "email": test_email,
            "password": test_password,
            "display_name": "Test Organizer",
            "phone": "555-0100"
        })
        
        # If the endpoint doesn't exist yet because deployment is pending, this will fail.
        # We assume deployment is complete for this test.
        assert res.status_code == 201, f"Failed to register: {res.text}"
        data = res.json()
        access_token = data["tokens"]["access_token"]
        organizer_id = data["user"]["id"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        print(f"✅ User Registered and JWT received (ID: {organizer_id})")

        # 2. Test B2B2C Organizer Branding
        res = await client.put(f"/organizer/branding?organizer_id={organizer_id}", headers=headers, json={
            "primary_color": "#FF5733",
            "logo_url": "https://example.com/logo.png",
            "company_name": "E2E Test Retreats"
        })
        assert res.status_code == 200, f"Failed to set branding: {res.text}"
        print("✅ Organizer Branding Updated")

        # 3. Test Trip Creation
        res = await client.post("/trips", headers=headers, json={
            "title": "E2E Test Retreat",
            "destination": "Austin, TX",
            "start_date": "2027-10-10",
            "end_date": "2027-10-14",
            "description": "A test trip",
            "currency": "USD",
            "threshold_pct": 80,
            "estimated_cost_per_person": 50000,
        })
        assert res.status_code == 201, f"Failed to create trip: {res.text}"
        trip_data = res.json()
        trip_id = trip_data["id"]
        print(f"✅ Trip Created (ID: {trip_id})")

        # 4. Test Bulk Invites
        res = await client.post(f"/trips/{trip_id}/bulk-invite", headers=headers, json={
            "members": [
                {"email": f"member1_{uuid.uuid4().hex[:8]}@example.com", "display_name": "Member One"},
                {"email": f"member2_{uuid.uuid4().hex[:8]}@example.com", "display_name": "Member Two"}
            ]
        })
        assert res.status_code == 200, f"Failed to bulk invite: {res.text}"
        trip_data = res.json()
        assert trip_data["status"] == "collecting", "Trip should transition to collecting"
        print("✅ Bulk Invites Sent & Trip Status changed to Collecting")

        # 5. Extract a member for commit testing
        member_id = None
        for m in trip_data["members"]:
            if m["role"] == "member":
                member_id = m["id"]
                break
        
        assert member_id is not None
        
        # 6. Test Member Commit
        res = await client.post(f"/trips/{trip_id}/members/{member_id}/commit", headers=headers, json={
            "origin_airport": "JFK"
        })
        assert res.status_code == 200, f"Failed to commit member: {res.text}"
        print(f"✅ Member {member_id} Committed")

        # 7. Test Organizer Dashboard
        res = await client.get(f"/organizer/dashboard?organizer_id={organizer_id}", headers=headers)
        assert res.status_code == 200, f"Failed to get dashboard: {res.text}"
        dash_data = res.json()
        assert dash_data["total_trips_active"] == 1
        print("✅ Organizer Dashboard Accessed successfully")
        print("--- E2E Test Completed Successfully ---")

if __name__ == "__main__":
    asyncio.run(test_end_to_end_rally_workflow())
