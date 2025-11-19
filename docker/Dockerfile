# Use official Python image
FROM python:3.11-slim

# Set environment variable for timezone
ENV TZ=Asia/Kolkata

# Install tzdata for timezone support
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Set the timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    wget \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxdamage1 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright playwright-stealth && playwright install --with-deps chromium

# Expose Flask API port
EXPOSE 9010

# Copy app files
COPY . .

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Create results directory
RUN mkdir -p /app/results && chmod 777 /app/results

# Run the scheduler
CMD ["sh", "-c", "python dcs_api.py & python main.py"]
