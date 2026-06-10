#!/bin/bash

OWNER="brovk2008"
REPO="Dataset_collector"
TAG="v3.0.3"

# Get the release ID
RELEASE_ID=$(curl -s "https://api.github.com/repos/$OWNER/$REPO/releases/tags/$TAG" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -z "$RELEASE_ID" ]; then
  echo "ERROR: Could not find release v3.0.3"
  echo "Creating release from tag..."
  
  # Create release from tag
  curl -X POST \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$OWNER/$REPO/releases" \
    -d "{\"tag_name\":\"$TAG\",\"name\":\"v3.0.3: Production Release\",\"draft\":false,\"prerelease\":false,\"make_latest\":\"true\"}"
else
  echo "Found release ID: $RELEASE_ID"
  echo "Updating to mark as latest..."
  
  # Update release to mark as latest
  curl -X PATCH \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$OWNER/$REPO/releases/$RELEASE_ID" \
    -d '{"draft":false,"prerelease":false,"make_latest":"true"}'
fi
