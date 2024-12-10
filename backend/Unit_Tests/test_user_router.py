from fastapi.testclient import TestClient
from backend.neu_sa.fastapp import app

client = TestClient(app)

def test_get_user_data():
    """Test the /user/{user_id} endpoint."""
    user_id = 1
    response = client.get(f"/user/{user_id}")
    assert response.status_code in [200, 403], f"Unexpected status code: {response.status_code}"

def test_update_user_profile():
    """Test updating user profile."""
    user_id = 1
    payload = {
        "college": "College of Engineering",
        "program_name": "Information Systems, MSIS",
        "program_id": "MP_IS_MSIS",
        "gpa": 3.5,
        "campus": "Boston"
    }
    response = client.put(f"/user/{user_id}/profile", json=payload)
    assert response.status_code in [200, 403], f"Unexpected status code: {response.status_code}"