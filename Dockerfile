FROM python:3.13-slim

WORKDIR /usr/src/app/questioner-bot

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files first for better caching
COPY pyproject.toml uv.lock* /usr/src/app/questioner-bot/

# Install system dependencies and Microsoft ODBC driver
RUN apt-get update && \
    apt-get install -y curl gnupg unixodbc-dev && \
    # Add Microsoft repository
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-archive-keyring.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    # Update package lists and install ODBC driver
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    # Install Python dependencies with uv
    uv sync --frozen && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /usr/src/app/questioner-bot

# Set the PATH to include the virtual environment
ENV PATH="/usr/src/app/questioner-bot/.venv/bin:$PATH"