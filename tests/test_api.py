"""Test cases for the Mergington High School API"""

import pytest


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Soccer Team" in data

    def test_activity_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_initial_participants(self, client):
        """Test that activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_successful_signup(self, client):
        """Test successful student signup"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_duplicate_signup(self, client):
        """Test that duplicate signup is prevented"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_full_activity(self, client):
        """Test that signup is prevented when activity is full"""
        # Fill up Chess Club (max 12 participants, currently has 2)
        for i in range(10):
            response = client.post(
                f"/activities/Chess Club/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Next signup should fail
        response = client.post(
            "/activities/Chess Club/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        assert "Activity is full" in response.json()["detail"]

    def test_signup_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=encoded@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_successful_unregister(self, client):
        """Test successful student unregistration"""
        email = "michael@mergington.edu"
        
        # Verify student is initially registered
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
        
        # Unregister student
        response = client.delete(
            f"/activities/Chess Club/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify student was removed
        activities = client.get("/activities").json()
        assert email not in activities["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_signed_up(self, client):
        """Test unregister when student is not signed up"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_register_then_unregister(self, client):
        """Test full cycle of registering and unregistering"""
        email = "cycle@mergington.edu"
        
        # Register
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 200
        
        # Verify registration
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify unregistration
        activities = client.get("/activities").json()
        assert email not in activities["Chess Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity management"""

    def test_spots_calculation(self, client):
        """Test that spots remaining are calculated correctly"""
        activities = client.get("/activities").json()
        
        chess_club = activities["Chess Club"]
        current_count = len(chess_club["participants"])
        max_count = chess_club["max_participants"]
        
        assert current_count == 2
        assert max_count == 12
        assert max_count - current_count == 10  # spots remaining


class TestMultipleActivities:
    """Tests for managing multiple activities"""

    def test_student_in_multiple_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multitasker@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Sign up for Soccer Team
        response2 = client.post(f"/activities/Soccer Team/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify student is in both
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Soccer Team"]["participants"]

    def test_all_activities_accessible(self, client):
        """Test that all 9 activities are accessible"""
        activities = client.get("/activities").json()
        
        expected_activities = [
            "Chess Club", "Soccer Team", "Swimming Club", "Art Studio",
            "Drama Club", "Debate Team", "Science Club", "Programming Class",
            "Gym Class"
        ]
        
        for activity_name in expected_activities:
            assert activity_name in activities
