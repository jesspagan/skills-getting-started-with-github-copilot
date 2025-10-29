"""
Test cases for the Mergington High School API endpoints.
"""



class TestRootEndpoint:
    """Test cases for the root endpoint."""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Test cases for the /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all available activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) >= 9  # Should have at least 9 activities
        
        # Check that essential activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
    def test_activity_structure(self, client, reset_activities):
        """Test that each activity has the correct structure."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            
            # Check that max_participants is positive
            assert activity_data["max_participants"] > 0


class TestSignupEndpoint:
    """Test cases for the signup endpoint."""
    
    def test_successful_signup(self, client, reset_activities, sample_email, sample_activity):
        """Test successful signup for an activity."""
        response = client.post(f"/activities/{sample_activity}/signup?email={sample_email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert sample_email in data["message"]
        assert sample_activity in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert sample_email in activities_data[sample_activity]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client, reset_activities, sample_email):
        """Test signup for an activity that doesn't exist."""
        response = client.post(f"/activities/Nonexistent Activity/signup?email={sample_email}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_duplicate_signup_prevention(self, client, reset_activities, sample_activity):
        """Test that duplicate signups are prevented."""
        # Use an email that's already in the sample activity
        existing_email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(f"/activities/{sample_activity}/signup?email={existing_email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_encoded_activity_name(self, client, reset_activities, sample_email):
        """Test signup with URL-encoded activity name."""
        activity_name = "Programming Class"
        encoded_name = "Programming%20Class"
        
        response = client.post(f"/activities/{encoded_name}/signup?email={sample_email}")
        
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert sample_email in activities_data[activity_name]["participants"]
    
    def test_signup_with_encoded_email(self, client, reset_activities, sample_activity):
        """Test signup with URL-encoded email."""
        email = "test+student@mergington.edu"
        encoded_email = "test%2Bstudent%40mergington.edu"
        
        response = client.post(f"/activities/{sample_activity}/signup?email={encoded_email}")
        
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[sample_activity]["participants"]


class TestUnregisterEndpoint:
    """Test cases for the unregister endpoint."""
    
    def test_successful_unregister(self, client, reset_activities, sample_activity):
        """Test successful unregistration from an activity."""
        # Use an existing participant
        existing_email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.delete(f"/activities/{sample_activity}/unregister?email={existing_email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert existing_email in data["message"]
        assert sample_activity in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert existing_email not in activities_data[sample_activity]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client, reset_activities, sample_email):
        """Test unregistration from an activity that doesn't exist."""
        response = client.delete(f"/activities/Nonexistent Activity/unregister?email={sample_email}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_not_registered_participant(self, client, reset_activities, sample_activity):
        """Test unregistration of a participant who isn't registered."""
        unregistered_email = "not.registered@mergington.edu"
        
        response = client.delete(f"/activities/{sample_activity}/unregister?email={unregistered_email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_with_encoded_parameters(self, client, reset_activities):
        """Test unregistration with URL-encoded parameters."""
        # First, sign up a participant with special characters
        email = "test+student@mergington.edu"
        activity_name = "Programming Class"
        
        # Sign up first (using urllib to properly encode)
        import urllib.parse
        encoded_email_signup = urllib.parse.quote(email)
        encoded_activity_signup = urllib.parse.quote(activity_name)
        
        signup_response = client.post(f"/activities/{encoded_activity_signup}/signup?email={encoded_email_signup}")
        assert signup_response.status_code == 200
        
        # Then unregister with encoded parameters
        response = client.delete(f"/activities/{encoded_activity_signup}/unregister?email={encoded_email_signup}")
        
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]


class TestIntegrationScenarios:
    """Integration test scenarios."""
    
    def test_signup_and_unregister_flow(self, client, reset_activities, sample_email, sample_activity):
        """Test complete signup and unregister flow."""
        # Initial state - check participant count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[sample_activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{sample_activity}/signup?email={sample_email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        assert len(after_signup_data[sample_activity]["participants"]) == initial_count + 1
        assert sample_email in after_signup_data[sample_activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{sample_activity}/unregister?email={sample_email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        after_unregister_response = client.get("/activities")
        after_unregister_data = after_unregister_response.json()
        assert len(after_unregister_data[sample_activity]["participants"]) == initial_count
        assert sample_email not in after_unregister_data[sample_activity]["participants"]
    
    def test_multiple_activities_signup(self, client, reset_activities, sample_email):
        """Test signing up for multiple activities."""
        activities_to_test = ["Chess Club", "Programming Class", "Art Club"]
        
        for activity in activities_to_test:
            response = client.post(f"/activities/{activity}/signup?email={sample_email}")
            assert response.status_code == 200
        
        # Verify participant is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity in activities_to_test:
            assert sample_email in activities_data[activity]["participants"]
    
    def test_participant_count_consistency(self, client, reset_activities):
        """Test that participant counts remain consistent across operations."""
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity_name, activity_data in activities_data.items():
            participant_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            
            # Participant count should not exceed maximum
            assert participant_count <= max_participants
            
            # All participants should have valid email format
            for participant in activity_data["participants"]:
                assert "@" in participant
                assert "." in participant