#!/bin/bash

# Deployment Script for Dashboard
# Usage: ./deploy.sh [GITHUB_TOKEN]

TOKEN=$1

if [ -z "$TOKEN" ]; then
  if [ -f "pat.txt" ]; then
    TOKEN=$(cat pat.txt | tr -d '\n')
    echo "Using token from pat.txt"
  else
    echo "Error: No token provided and pat.txt not found."
    echo "Usage: ./deploy.sh <YOUR_GITHUB_TOKEN>"
    exit 1
  fi
fi

echo "Pushing to GitHub..."
cd dashboard
git push "https://vzbb:$TOKEN@github.com/vzbb/vegacase.git" main

if [ $? -eq 0 ]; then
  echo "✅ Push successful! Vercel should auto-deploy shortly."
else
  echo "❌ Push failed. Please check your token permissions (needs 'repo' scope or Write access)."
fi
