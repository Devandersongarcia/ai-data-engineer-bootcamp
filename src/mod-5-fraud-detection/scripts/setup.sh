#!/bin/bash

# UberEats Fraud Detection System - Setup Script
# This script sets up the development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Python
    if ! command_exists python3; then
        missing_deps+=("python3")
    else
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major_version=$(echo "$python_version" | cut -d'.' -f1)
        local minor_version=$(echo "$python_version" | cut -d'.' -f2)
        
        if [[ $major_version -lt 3 ]] || [[ $major_version -eq 3 && $minor_version -lt 9 ]]; then
            error "Python 3.9+ is required. Found: $python_version"
            missing_deps+=("python3.9+")
        else
            success "Python $python_version found"
        fi
    fi
    
    # Check pip
    if ! command_exists pip3; then
        missing_deps+=("pip3")
    fi
    
    # Check Docker
    if ! command_exists docker; then
        missing_deps+=("docker")
    else
        if ! docker info >/dev/null 2>&1; then
            error "Docker is installed but not running"
            missing_deps+=("docker (running)")
        else
            success "Docker is running"
        fi
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        missing_deps+=("docker-compose")
    fi
    
    # Check git
    if ! command_exists git; then
        missing_deps+=("git")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo
        error "Please install the missing dependencies and run this script again."
        exit 1
    fi
    
    success "All prerequisites are met"
}

# Setup Python virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        success "Virtual environment created"
    else
        log "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [[ -f "requirements.txt" ]]; then
        log "Installing production dependencies..."
        pip install -r requirements.txt
    fi
    
    if [[ -f "requirements-test.txt" ]]; then
        log "Installing test dependencies..."
        pip install -r requirements-test.txt
    fi
    
    success "Python environment setup complete"
}

# Setup environment configuration
setup_environment() {
    log "Setting up environment configuration..."
    
    cd "$PROJECT_ROOT"
    
    # Create .env from template if it doesn't exist
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            cp ".env.example" ".env"
            success "Created .env from template"
            warning "Please update .env file with your configuration"
            warning "Especially set your OPENAI_API_KEY"
        else
            error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    else
        log ".env file already exists"
    fi
    
    # Create necessary directories
    local directories=("logs" "data" "notebooks")
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
    
    success "Environment configuration complete"
}

# Setup pre-commit hooks
setup_precommit() {
    log "Setting up pre-commit hooks..."
    
    cd "$PROJECT_ROOT"
    
    # Install pre-commit if not already installed
    if ! command_exists pre-commit; then
        pip install pre-commit
    fi
    
    # Create pre-commit config if it doesn't exist
    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
EOF
        success "Created pre-commit configuration"
    fi
    
    # Install pre-commit hooks
    pre-commit install
    
    success "Pre-commit hooks installed"
}

# Initialize development services
init_dev_services() {
    log "Initializing development services..."
    
    cd "$PROJECT_ROOT"
    
    # Check if Docker Compose file exists
    if [[ ! -f "docker-compose.yml" ]]; then
        error "docker-compose.yml not found"
        exit 1
    fi
    
    # Start infrastructure services only
    log "Starting infrastructure services (Kafka, Redis, PostgreSQL)..."
    docker-compose up -d zookeeper kafka redis postgres
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Setup Kafka topics
    log "Setting up Kafka topics..."
    docker-compose up kafka-setup
    
    success "Development services initialized"
}

# Run initial tests
run_tests() {
    log "Running initial tests..."
    
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run fast tests
    if [[ -f "run_tests.py" ]]; then
        python run_tests.py --mode fast
    else
        # Fallback to pytest
        python -m pytest tests/ -x --tb=short -q
    fi
    
    success "Initial tests passed"
}

# Generate sample data
generate_sample_data() {
    log "Generating sample data..."
    
    cd "$PROJECT_ROOT"
    
    # Create sample data directory
    mkdir -p data/samples
    
    # Generate sample order data
    cat > data/samples/sample_orders.json << EOF
[
  {
    "order_id": "order_001",
    "user_key": "user_001",
    "total_amount": 25.50,
    "item_count": 2,
    "restaurant_id": "rest_001",
    "delivery_lat": 37.7749,
    "delivery_lng": -122.4194,
    "order_timestamp": "2024-01-15T12:30:00Z",
    "payment_method": "credit_card",
    "account_age_days": 90
  },
  {
    "order_id": "order_002",
    "user_key": "user_002",
    "total_amount": 500.00,
    "item_count": 20,
    "restaurant_id": "rest_002", 
    "delivery_lat": 40.7128,
    "delivery_lng": -74.0060,
    "order_timestamp": "2024-01-15T03:30:00Z",
    "payment_method": "new_credit_card",
    "account_age_days": 1,
    "orders_today": 15,
    "payment_failures_today": 5
  }
]
EOF
    
    success "Sample data generated"
}

# Create development script shortcuts
create_shortcuts() {
    log "Creating development shortcuts..."
    
    cd "$PROJECT_ROOT"
    
    # Create start script
    cat > start_dev.sh << 'EOF'
#!/bin/bash
# Quick start script for development

echo "🚨 Starting UberEats Fraud Detection System (Development)"
echo "========================================================="

# Activate virtual environment
source venv/bin/activate

# Start services
docker-compose up -d

echo "✅ System started successfully!"
echo ""
echo "📊 Dashboard: http://localhost:8501"
echo "🔗 API: http://localhost:8000"
echo "📄 API Docs: http://localhost:8000/docs"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f"
EOF
    chmod +x start_dev.sh
    
    # Create stop script
    cat > stop_dev.sh << 'EOF'
#!/bin/bash
# Quick stop script for development

echo "🛑 Stopping UberEats Fraud Detection System"
docker-compose down
echo "✅ System stopped"
EOF
    chmod +x stop_dev.sh
    
    # Create test script shortcut
    cat > test.sh << 'EOF'
#!/bin/bash
# Quick test script

source venv/bin/activate
python run_tests.py "$@"
EOF
    chmod +x test.sh
    
    success "Development shortcuts created"
}

# Print setup summary
print_summary() {
    echo
    echo "🎉 Setup Complete!"
    echo "=================="
    echo
    echo "Your UberEats Fraud Detection System is ready for development!"
    echo
    echo "📁 Project Structure:"
    echo "  ├── src/                 # Source code"
    echo "  ├── tests/              # Test files"
    echo "  ├── rag/                # Airflow DAGs"
    echo "  ├── scripts/            # Deployment scripts"
    echo "  ├── venv/               # Python virtual environment"
    echo "  └── .env                # Environment configuration"
    echo
    echo "🚀 Quick Start Commands:"
    echo "  ./start_dev.sh          # Start development environment"
    echo "  ./stop_dev.sh           # Stop development environment"
    echo "  ./test.sh               # Run tests"
    echo "  ./scripts/deploy.sh     # Full deployment"
    echo
    echo "🔧 Manual Commands:"
    echo "  source venv/bin/activate                  # Activate Python environment"
    echo "  python src/main.py --mode api            # Start API mode"
    echo "  python run_dashboard.py                  # Start dashboard"
    echo "  python run_tests.py --mode all           # Run all tests"
    echo "  docker-compose up -d                     # Start all services"
    echo
    echo "📊 Service URLs (after starting):"
    echo "  Dashboard: http://localhost:8501"
    echo "  API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo
    echo "⚠️  Important Notes:"
    echo "  1. Update your .env file with your OpenAI API key"
    echo "  2. The system requires Docker to be running"
    echo "  3. Run tests with: ./test.sh"
    echo "  4. For Airflow: cd rag && astro dev start"
    echo
    success "Happy coding! 🚀"
}

# Main setup function
main() {
    echo "🚨 UberEats Fraud Detection System - Setup"
    echo "=========================================="
    echo
    
    check_prerequisites
    setup_venv
    setup_environment
    setup_precommit
    init_dev_services
    run_tests
    generate_sample_data
    create_shortcuts
    print_summary
}

# Handle errors
trap 'error "Setup failed!"; exit 1' ERR

# Run main function
main