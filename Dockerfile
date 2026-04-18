# --- Stage 1: Build the C++ Pybind11 Engine ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install compilation dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libfluidsynth-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Pybind11
COPY hymn_remaker/requirements.txt .
RUN pip install --no-cache-dir pybind11

# Copy source and build
COPY Makefile .
COPY src/engine/ src/engine/
RUN make extension

# --- Stage 2: Runtime Environment ---
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fluidsynth \
    fluid-soundfont-gm \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies and install
COPY hymn_remaker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy compiled C++ extension from builder
COPY --from=builder /build/hymn_player_ext*.so ./

# Copy the rest of the application
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Default to running the Streamlit UI, but can be overridden in docker-compose for daemon mode
CMD ["python", "-m", "streamlit", "run", "hymn_remaker/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
