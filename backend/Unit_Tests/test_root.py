import sys
import os

# Add the backend directory to PYTHONPATH dynamically
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from neu_sa.fastapp import app  # Import after updating sys.path

from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200, "Root endpoint should return status 200"
    assert response.json() == {"message": "Welcome to the NEU-SA backend API!"}, "Unexpected response from root endpoint"