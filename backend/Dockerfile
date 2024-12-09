FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the project files
COPY . .

# Install dependencies using Poetry
RUN pip install poetry && poetry install --no-dev

# Expose the port your backend API runs on (e.g., FastAPI defaults to 8000)
EXPOSE 8000

# Run the backend application directly with Poetry and Uvicorn
CMD ["poetry", "run", "uvicorn", "neu_sa.fastapp:app", "--host", "0.0.0.0", "--port", "8000"]
