# Setup container
FROM python:latest
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command to run your app
CMD ["python", "main.py"]
