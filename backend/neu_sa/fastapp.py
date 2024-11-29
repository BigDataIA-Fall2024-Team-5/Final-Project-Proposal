from fastapi import FastAPI
from neu_sa.routers.auth import auth_router
from neu_sa.routers.user_router import user_router
from neu_sa.routers.transcript_router import transcript_router
from neu_sa.routers.task_detection_agent import task_detection_agent
from dotenv import load_dotenv
import os
import uvicorn

# Load environment variables
load_dotenv()

# Initialize the FastAPI app
app = FastAPI()

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(task_detection_agent, prefix="/chat", tags=["chat"])
app.include_router(transcript_router, prefix="/transcripts", tags=["Transcript Processing"])

# Root endpoint for health check
@app.get("/")
def read_root():
    return {"message": "Welcome to the NEU-SA backend API!"}

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("neu_sa.fastapp:app", host="0.0.0.0", port=port, reload=True)