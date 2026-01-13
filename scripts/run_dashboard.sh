#!/usr/bin/env bash
# Launch the AWS to OpenStack migration dashboard

set -e

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export DATABASE_URL='postgresql://user:pass@localhost:5432/aws2openstack'"
    echo ""
    echo "Or create a .env file with DATABASE_URL and run:"
    echo "  source .env"
    echo "  $0"
    exit 1
fi

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Launch Streamlit
echo "🚀 Launching AWS to OpenStack Migration Dashboard..."
echo "📍 Database: $DATABASE_URL"
echo ""

cd "$PROJECT_ROOT"
streamlit run src/aws2openstack/dashboard/app.py
