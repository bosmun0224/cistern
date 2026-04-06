#!/bin/bash
# init.sh - Initialize Terraform for the cistern project
set -e

cd "$(dirname "$0")"

echo "=== Cistern Infrastructure Init ==="

# Check for terraform
if ! command -v terraform &> /dev/null; then
    echo "ERROR: terraform not found. Install with: brew install terraform"
    exit 1
fi

# Check for tfvars
if [ ! -f "terraform.tfvars" ]; then
    echo "Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "EDIT terraform.tfvars with your project ID before running 'terraform apply'"
fi

# Check for gcloud auth
if ! command -v gcloud &> /dev/null; then
    echo "WARNING: gcloud CLI not found. Install with: brew install google-cloud-sdk"
    echo "You'll need it to authenticate: gcloud auth application-default login"
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
