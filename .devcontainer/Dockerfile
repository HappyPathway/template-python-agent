# Use Python 3.11 as base image
FROM mcr.microsoft.com/devcontainers/python:3.12

# Prevent apt from showing prompts
ENV DEBIAN_FRONTEND=noninteractive

# Python environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set environment directory
WORKDIR /workspace

# Install base Python packages
RUN pip install --no-cache-dir \
    black \
    pylint \
    pytest \
    pytest-cov \
    isort \
    python-dotenv

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog
