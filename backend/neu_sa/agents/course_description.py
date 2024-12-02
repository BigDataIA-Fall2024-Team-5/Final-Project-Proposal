from pinecone import Index
from langchain_core.tools import tool
import os

class CourseDescriptionTool:
    def __init__(self, index_name="course-description-index"):
        self.index = Index(index_name)

    @tool
    def fetch_course_description(self, query):
        """Retrieve course descriptions and related metadata."""
        embedding_client = ...  # Initialize your embedding client here
        embedding = embedding_client.embed_query(query)
        results = self.index.query(embedding, top_k=5, include_metadata=True)
        return {
            "results": [
                {
                    "course_code": match.metadata["course_code"],
                    "course_name": match.metadata["course_name"],
                    "description": match.metadata["description"],
                    "prerequisites": match.metadata["prerequisites"],
                    "corequisites": match.metadata["corequisites"],
                    "credits": match.metadata["credits"],
                    "subject_code": match.metadata["subject_code"],
                }
                for match in results["matches"]
            ]
        }
