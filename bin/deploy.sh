#!/bin/bash

# Script name: deploy.sh
# Description: Deploys a Docker image to Google Cloud Platform using GKE or Cloud Run.
#
# Usage: ./deploy.sh <PROJECT_ID> <IMAGE_NAME> <IMAGE_TAG> <REGION> <SERVICE_NAME> <DEPLOYMENT_TYPE> [<DEPLOYMENT_YAML_FILE>] [<SERVICE_YAML_FILE>]
#
# Required inputs:
# - PROJECT_ID: The ID of the Google Cloud Platform project to deploy to.
# - IMAGE_NAME: The name of the Docker image to deploy.
# - IMAGE_TAG: The tag of the Docker image to deploy.
# - REGION: The region to deploy the Docker image to (for Cloud Run).
# - SERVICE_NAME: The name of the Cloud Run service to deploy (for Cloud Run).
# - DEPLOYMENT_TYPE: The type of deployment to use (either 'gke' or 'cloudrun').
#
# Optional inputs:
# - DEPLOYMENT_YAML_FILE: The path to the Kubernetes deployment YAML file (for GKE).
# - SERVICE_YAML_FILE: The path to the Kubernetes service YAML file (for GKE).

# Input variables
PROJECT_ID="$1"
IMAGE_NAME="$2"
IMAGE_TAG="$3"
REGION="$4"
SERVICE_NAME="$5"
DEPLOYMENT_TYPE="$6"
DEPLOYMENT_YAML_FILE="$7"
SERVICE_YAML_FILE="$8"

# Deploy the Docker image
if [[ "$DEPLOYMENT_TYPE" == "gke" ]]; then
  # Authenticate with GKE
  gcloud auth login
  gcloud config set project $PROJECT_ID
  gcloud auth configure-docker

  # Push Docker image to Google Container Registry (GCR)
  docker tag $IMAGE_NAME:$IMAGE_TAG gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG
  docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG

  # Create Kubernetes deployment and service
  kubectl apply -f $DEPLOYMENT_YAML_FILE
  kubectl apply -f $SERVICE_YAML_FILE

  echo "Deployment complete!"

elif [[ "$DEPLOYMENT_TYPE" == "cloudrun" ]]; then
  # Authenticate with Cloud Run
  gcloud config set project $PROJECT_ID
  gcloud auth configure-docker

  # Push Docker image to Google Container Registry (GCR)
  docker tag $IMAGE_NAME:$IMAGE_TAG gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG
  docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG

  # Deploy Docker image to Cloud Run
  gcloud run deploy $SERVICE_NAME --image gcr.io/$PROJECT_ID/$IMAGE_NAME:$IMAGE_TAG --platform managed --region $REGION

  echo "Deployment complete!"

else
  echo "Invalid deployment type. Please choose either 'gke' or 'cloudrun'."
fi
