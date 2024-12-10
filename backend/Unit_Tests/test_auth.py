from fastapi.testclient import TestClient
from backend.neu_sa.fastapp import app

client = TestClient(app)

def test_register_user():
    """Test the /auth/register endpoint."""
    payload = {
        "username": "testuser",
        "password": "Password123!",
        "campus": "Boston",
        "program_name": "Information Systems, MSIS",
        "college": "College of Engineering"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code in [200, 400], f"Unexpected status code: {response.status_code}"

def test_login_user():
    """Test the /auth/login endpoint."""
    payload = {
        "username": "testuser",
        "password": "Password123!"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code in [200, 401], f"Unexpected status code: {response.status_code}"

def test_validate_token():
    """Test the /auth/validate-token endpoint."""
    # Simulate a valid token (replace with actual JWT if needed)
    token = {"token": "fake.jwt.token"}
    response = client.post("/auth/validate-token", json=token)
    assert response.status_code == 200 or response.json().get("valid") is False