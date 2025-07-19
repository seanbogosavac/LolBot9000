#!/bin/bash

# Exit on error
set -e

# Project name
PROJECT_NAME="LolBot9000"

echo "Setting up $PROJECT_NAME..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
else
  echo "Virtual environment already exists."
fi

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
  echo "Installing dependencies from requirements.txt..."
  pip install -r requirements.txt
else
  echo "No requirements.txt found."
fi

echo "Installation complete. To activate the environment, run:"
echo "source venv/bin/activate"
