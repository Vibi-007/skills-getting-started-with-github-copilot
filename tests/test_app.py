"""Tests for the Mergington High School API"""

import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestRoot:
    """Tests for the root endpoint"""

    def test_root_redirect(self):
        """Test that root endpoint redirects to static index"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities(self):
        """Test that we can fetch all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
        
        # Check for expected activity fields
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_activities_contain_chess_club(self):
        """Test that Chess Club activity exists in results"""
        response = client.get("/activities")
        activities = response.json()
        assert "Chess Club" in activities

    def test_activities_have_initial_participants(self):
        """Test that some activities have initial participants"""
        response = client.get("/activities")
        activities = response.json()
        
        # At least one activity should have participants
        has_participants = any(
            len(activity["participants"]) > 0 
            for activity in activities.values()
        )
        assert has_participants


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        assert "test@mergington.edu" in response.json()["message"]

    def test_signup_nonexistent_activity(self):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_duplicate_registration(self):
        """Test that duplicate signup raises error"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Basketball%20Team/signup?email=" + email
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            "/activities/Basketball%20Team/signup?email=" + email
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()

    def test_signup_multiple_activities(self):
        """Test that a student can sign up for multiple activities"""
        email = "multiactivity@mergington.edu"
        
        response1 = client.post(
            "/activities/Chess%20Club/signup?email=" + email
        )
        assert response1.status_code == 200
        
        response2 = client.post(
            "/activities/Drama%20Club/signup?email=" + email
        )
        assert response2.status_code == 200


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_from_activity(self):
        """Test successful unregistration from an activity"""
        email = "unregister@mergington.edu"
        
        # First, sign up
        client.post(f"/activities/Tennis%20Club/signup?email={email}")
        
        # Then unregister
        response = client.post(
            f"/activities/Tennis%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_unregister_nonexistent_activity(self):
        """Test unregister from non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404

    def test_unregister_not_signed_up(self):
        """Test unregister when not signed up returns error"""
        response = client.post(
            "/activities/Art%20Studio/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()

    def test_signup_then_unregister_removes_participant(self):
        """Test that signup followed by unregister properly removes participant"""
        email = "removeme@mergington.edu"
        
        # Get initial participant count
        initial = client.get("/activities").json()
        initial_count = len(initial["Debate Team"]["participants"])
        
        # Sign up
        client.post("/activities/Debate%20Team/signup?email=" + email)
        
        # Verify signup increased count
        after_signup = client.get("/activities").json()
        assert len(after_signup["Debate Team"]["participants"]) == initial_count + 1
        
        # Unregister
        client.post("/activities/Debate%20Team/unregister?email=" + email)
        
        # Verify count is back to initial
        after_unregister = client.get("/activities").json()
        assert len(after_unregister["Debate Team"]["participants"]) == initial_count


class TestEndpointIntegration:
    """Integration tests combining multiple endpoints"""

    def test_full_signup_flow(self):
        """Test complete signup-unregister flow"""
        email = "integration@mergington.edu"
        activity = "Science%20Club"
        
        # Get initial state
        initial_activities = client.get("/activities").json()
        initial_participants = initial_activities["Science Club"]["participants"].copy()
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_after_signup = client.get("/activities").json()
        assert email in activities_after_signup["Science Club"]["participants"]
        
        # Unregister
        unregister_response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        activities_after_unregister = client.get("/activities").json()
        assert activities_after_unregister["Science Club"]["participants"] == initial_participants
