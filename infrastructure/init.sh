#!/bin/bash
# init.sh - Initialize Terraform for the cistern project
set -e

cd "$(dirname "$0")"

echo "=== Cistern Infrastructure Init ==="
echo ""

# Check for terraform
if ! command -v terraform &> /dev/null; then
    echo "ERROR: terraform not found. Install with: brew install terraform"
    exit 1
fi
echo "Terraform: $(terraform version -json | python3 -c 'import sys,json; print(json.load(sys.stdin)["terraform_version"])' 2>/dev/null || terraform version | head -1)"

# Check for gcloud
if ! command -v gcloud &> /dev/null; then
    echo ""
    echo "ERROR: gcloud CLI not found. Install with: brew install google-cloud-sdk"
    echo "Then run: gcloud auth application-default login"
    exit 1
fi

# Show current gcloud context
echo ""
echo "--- GCP Account Info ---"
ACCOUNT=$(gcloud config get-value account 2>/dev/null)
PROJECT=$(gcloud config get-value project 2>/dev/null)
echo "  Account: ${ACCOUNT:-Not logged in}"
echo "  Project: ${PROJECT:-Not set}"

# Check if logged in
if [ -z "$ACCOUNT" ] || [ "$ACCOUNT" = "(unset)" ]; then
    echo ""
    echo "Not logged in. Run:"
    echo "  gcloud auth login"
    echo "  gcloud auth application-default login"
    exit 1
fi

# Check application-default credentials
if [ ! -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
    echo ""
    echo "WARNING: No application-default credentials found."
    echo "  Run: gcloud auth application-default login"
fi

# List billing accounts
echo ""
echo "--- Billing Accounts ---"
gcloud billing accounts list --format="table(name, displayName, open)" 2>/dev/null || echo "  Could not list billing accounts"

# Check for tfvars
echo ""
if [ ! -f "terraform.tfvars" ]; then
    echo "Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "  EDIT terraform.tfvars with your project ID and billing account"
else
    echo "--- terraform.tfvars ---"
    cat terraform.tfvars
fi

echo ""
echo "Initializing Terraform..."
terraform init

echo ""
echo "Validating configuration..."
terraform validate

echo ""
echo "=== Init complete ==="
echo "Next steps:"
echo "  1. Edit terraform.tfvars with your Firebase project ID"
echo "  2. Run: gcloud auth application-default login"
echo "  3. Run: terraform plan"
echo "  4. Run: terraform apply"
