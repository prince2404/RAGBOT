# Dockerfile
# Use a supported Debian-based Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install any dependencies specified in requirements.txt
# If you don't have a requirements.txt, create one using: pip freeze > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Uvicorn will listen on (default is 8000)
EXPOSE 8000

# Set environment variables (if needed - load from .env during runtime)
# Use OpenRouter API key - set in Render dashboard or .env file
# ENV OPENROUTER_API_KEY=your_openrouter_api_key

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
