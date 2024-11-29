from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

# Initialize router
task_detection_agent = APIRouter()

# Input model for query
class QueryModel(BaseModel):
    query: str

# Dummy task detection endpoint
@task_detection_agent.post("/detect_task")
async def detect_task(query: QueryModel):
    """
    Dummy endpoint to handle chatbot queries and return a static response.
    """
    try:
        if not query.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        # Static response for testing
        dummy_response = {
            "response": f"Test reply for your query: {query.query}",
            "status": "success",
        }

        return dummy_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
