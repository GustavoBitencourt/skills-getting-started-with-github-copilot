"""
Tests for the Mergington High School API
"""
import pytest


class TestRoot:
    """Tests for the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that get_activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 9
        
        # Check that all expected activities are present
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Soccer Team",
            "Track & Field",
            "Art Club",
            "Drama Club",
            "Debate Team",
            "Science Club"
        ]
        for activity in expected_activities:
            assert activity in data

    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_chess_club_initial_participants(self, client):
        """Test that Chess Club has initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_new_participant_is_added_to_list(self, client):
        """Test that a new participant is actually added to the participants list"""
        # Sign up
        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        
        assert "newstudent@mergington.edu" in data["Chess Club"]["participants"]
        assert len(data["Chess Club"]["participants"]) == 3

    def test_signup_duplicate_participant_fails(self, client):
        """Test that signing up an already registered participant fails"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_with_special_characters_in_email(self, client):
        """Test that signup works with emails containing special characters"""
        email = "john.doe+test@mergington.edu"
        # URL encode the email to properly handle special characters
        from urllib.parse import quote
        encoded_email = quote(email, safe='@')
        
        response = client.post(
            f"/activities/Programming Class/signup?email={encoded_email}"
        )
        assert response.status_code == 200
        
        # Verify in activities list
        response = client.get("/activities")
        data = response.json()
        assert email in data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for the POST /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "michael@mergington.edu" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregistering actually removes the participant"""
        # Unregister
        client.post("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]
        assert len(data["Chess Club"]["participants"]) == 1
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant_fails(self, client):
        """Test that unregistering a non-existent participant fails"""
        response = client.post(
            "/activities/Chess Club/unregister?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_from_nonexistent_activity_fails(self, client):
        """Test that unregistering from a non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_then_unregister_workflow(self, client):
        """Test a complete signup -> unregister workflow"""
        new_email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={new_email}")
        assert response.status_code == 200
        
        # Verify signed up
        response = client.get("/activities")
        data = response.json()
        assert new_email in data[activity]["participants"]
        
        # Unregister
        response = client.post(f"/activities/{activity}/unregister?email={new_email}")
        assert response.status_code == 200
        
        # Verify unregistered
        response = client.get("/activities")
        data = response.json()
        assert new_email not in data[activity]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity limits"""

    def test_activity_max_participants_field_exists(self, client):
        """Test that activities have max_participants field"""
        response = client.get("/activities")
        data = response.json()
        
        for activity in data.values():
            assert "max_participants" in activity
            assert isinstance(activity["max_participants"], int)

    def test_multiple_signups_increase_participant_count(self, client):
        """Test that multiple signups increase the participant count"""
        activity = "Gym Class"
        
        # Get initial count
        response = client.get("/activities")
        data = response.json()
        initial_count = len(data[activity]["participants"])
        
        # Sign up multiple participants
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        data = response.json()
        assert len(data[activity]["participants"]) == initial_count + 3
        
        for email in emails:
            assert email in data[activity]["participants"]
