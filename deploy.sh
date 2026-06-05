#!/usr/bin/env bash

# ==============================================================================
# AIOps Command Center Build and Deployment Script
# ==============================================================================

set -e

# Terminal Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}             BUILDING & DEPLOYING AIOPS COMMAND CENTER                ${NC}"
echo -e "${CYAN}======================================================================${NC}"

# Define project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

print_step() {
    echo -e "\n${BLUE}>>> [STEP] $1...${NC}"
}

# ------------------------------------------------------------------------------
# STEP 1: Build Docker Images inside Minikube environment
# ------------------------------------------------------------------------------
print_step "1/4: Configuring Minikube Docker Environment"
# Direct docker CLI to talk to minikube's docker daemon
eval $(minikube -p minikube docker-env)

print_step "2/4: Building payment-api Image"
echo -e "${YELLOW}Building Docker Image 'payment-api:latest'...${NC}"
docker build -t payment-api:latest ./payment-api

print_step "3/4: Building command-center Image"
echo -e "${YELLOW}Building Docker Image 'command-center:latest'...${NC}"
docker build -t command-center:latest ./command-center

# ------------------------------------------------------------------------------
# STEP 2: Deploy to Kubernetes
# ------------------------------------------------------------------------------
print_step "4/4: Deploying Manifests to Cluster"
kubectl apply -f kubernetes.yaml

echo -e "\n${YELLOW}Waiting for deployments to roll out...${NC}"
kubectl rollout status deployment/payment-api -n default --timeout=80s
kubectl rollout status deployment/command-center -n default --timeout=80s

MINIKUBE_IP=$(minikube ip)
CC_URL="http://${MINIKUBE_IP}:32009"

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}          AIOPS COMMAND CENTER DEPLOYED COMPLETED SUCCESSFULLY        ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "\n${YELLOW}Access Information:${NC}"
echo -e "----------------------------------------------------------------------"
echo -e "${CYAN}AIOps Command Center Dashboard:${NC}"
echo -e "   - URL: ${CC_URL}"
echo -e "   - NodePort: 32009"
echo -e "\n${CYAN}Alternatively, run this command to access it via localhost:${NC}"
echo -e "   - kubectl port-forward svc/command-center-service 8000:8000"
echo -e "     (Then visit http://localhost:8000)"
echo -e "----------------------------------------------------------------------\n"
