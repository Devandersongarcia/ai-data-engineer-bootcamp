#!/bin/bash

# UberEats Fraud Detection System - Deployment Script
# This script handles deployment of the fraud detection system in different environments

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
ENV_FILE="${PROJECT_ROOT}/.env"

# Default values
ENVIRONMENT="development"
SERVICES="all"
BUILD_FRESH="false"
RUN_TESTS="false"
SKIP_DEPS="false"

# Logging function
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

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy UberEats Fraud Detection System

OPTIONS:
    -e, --env ENVIRONMENT       Deployment environment (development|staging|production) [default: development]
    -s, --services SERVICES     Services to deploy (all|api|streaming|dashboard|infrastructure) [default: all]
    -b, --build                 Force rebuild of Docker images
    -t, --test                  Run tests before deployment
    --skip-deps                 Skip dependency checks
    -h, --help                  Show this help message

EXAMPLES:
    $0                                          # Deploy everything in development mode
    $0 -e production -s api                     # Deploy only API in production
    $0 -b -t                                    # Force rebuild and run tests
    $0 -e staging --services infrastructure     # Deploy only infrastructure in staging

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -s|--services)
                SERVICES="$2"
                shift 2
                ;;
            -b|--build)
                BUILD_FRESH="true"
                shift
                ;;
            -t|--test)
                RUN_TESTS="true"
                shift
                ;;
            --skip-deps)
                SKIP_DEPS="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_dependencies() {
    if [[ "$SKIP_DEPS" == "true" ]]; then
        warning "Skipping dependency checks"
        return 0
    fi

    log "Checking dependencies..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    success "All dependencies are available"
}

# Validate environment configuration
validate_environment() {
    log "Validating environment configuration..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        warning ".env file not found. Creating from template..."
        if [[ -f "${PROJECT_ROOT}/.env.example" ]]; then
            cp "${PROJECT_ROOT}/.env.example" "$ENV_FILE"
            warning "Please update .env file with your configuration before continuing."
            warning "Especially set your OPENAI_API_KEY"
        else
            error ".env.example file not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    # Check for required environment variables
    local required_vars=("OPENAI_API_KEY")
    local missing_vars=()
    
    # Source the .env file to check variables
    set -a
    source "$ENV_FILE"
    set +a
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]] || [[ "${!var}" == "your_"* ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing or incomplete environment variables:"
        for var in "${missing_vars[@]}"; do
            error "  - $var"
        done
        error "Please update your .env file and try again."
        exit 1
    fi
    
    success "Environment configuration is valid"
}

# Run tests if requested
run_tests() {
    if [[ "$RUN_TESTS" == "true" ]]; then
        log "Running tests before deployment..."
        
        cd "$PROJECT_ROOT"
        
        if [[ -f "run_tests.py" ]]; then
            python run_tests.py --mode fast
        else
            # Fallback to direct pytest
            python -m pytest tests/ -x --tb=short
        fi
        
        success "Tests passed successfully"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    local build_args=()
    
    if [[ "$BUILD_FRESH" == "true" ]]; then
        build_args+=("--no-cache")
        log "Building with --no-cache flag"
    fi
    
    # Build specific targets based on services
    case "$SERVICES" in
        "all")
            docker-compose build "${build_args[@]}" fraud-api fraud-streaming fraud-dashboard
            ;;
        "api")
            docker-compose build "${build_args[@]}" fraud-api
            ;;
        "streaming")
            docker-compose build "${build_args[@]}" fraud-streaming
            ;;
        "dashboard")
            docker-compose build "${build_args[@]}" fraud-dashboard
            ;;
        "infrastructure")
            log "Infrastructure services use pre-built images"
            ;;
        *)
            error "Unknown services option: $SERVICES"
            exit 1
            ;;
    esac
    
    success "Docker images built successfully"
}

# Deploy infrastructure services
deploy_infrastructure() {
    log "Deploying infrastructure services..."
    
    cd "$PROJECT_ROOT"
    
    # Start infrastructure services
    docker-compose up -d zookeeper kafka redis postgres
    
    # Wait for services to be ready
    log "Waiting for infrastructure services to be ready..."
    
    # Wait for Kafka
    local max_wait=60
    local wait_time=0
    while ! docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list &> /dev/null; do
        if [[ $wait_time -ge $max_wait ]]; then
            error "Kafka failed to start within $max_wait seconds"
            exit 1
        fi
        sleep 5
        wait_time=$((wait_time + 5))
        log "Waiting for Kafka... (${wait_time}s)"
    done
    
    # Setup Kafka topics
    docker-compose up kafka-setup
    
    success "Infrastructure services deployed successfully"
}

# Deploy application services
deploy_application() {
    log "Deploying application services..."
    
    cd "$PROJECT_ROOT"
    
    case "$SERVICES" in
        "all")
            docker-compose up -d fraud-api fraud-streaming fraud-dashboard
            ;;
        "api")
            docker-compose up -d fraud-api
            ;;
        "streaming")
            docker-compose up -d fraud-streaming
            ;;
        "dashboard")
            docker-compose up -d fraud-dashboard
            ;;
        *)
            # Infrastructure only, nothing to do
            return 0
            ;;
    esac
    
    success "Application services deployed successfully"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to become healthy..."
    
    cd "$PROJECT_ROOT"
    
    local services=()
    case "$SERVICES" in
        "all")
            services=("fraud-api" "fraud-streaming" "fraud-dashboard")
            ;;
        "api")
            services=("fraud-api")
            ;;
        "streaming")
            services=("fraud-streaming")
            ;;
        "dashboard")
            services=("fraud-dashboard")
            ;;
        *)
            return 0
            ;;
    esac
    
    for service in "${services[@]}"; do
        log "Checking health of $service..."
        
        local max_wait=120
        local wait_time=0
        
        while [[ $wait_time -lt $max_wait ]]; do
            if docker-compose ps "$service" | grep -q "Up (healthy)"; then
                success "$service is healthy"
                break
            elif docker-compose ps "$service" | grep -q "Up"; then
                log "$service is running but not yet healthy..."
            else
                warning "$service is not running"
            fi
            
            sleep 10
            wait_time=$((wait_time + 10))
            log "Waiting for $service health check... (${wait_time}s)"
        done
        
        if [[ $wait_time -ge $max_wait ]]; then
            warning "$service did not become healthy within $max_wait seconds"
            warning "You may need to check the logs: docker-compose logs $service"
        fi
    done
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo
    
    cd "$PROJECT_ROOT"
    docker-compose ps
    
    echo
    log "Service URLs:"
    
    if docker-compose ps fraud-api | grep -q "Up"; then
        echo "🔗 Fraud Detection API: http://localhost:8000"
        echo "   Health Check: http://localhost:8000/health"
        echo "   API Docs: http://localhost:8000/docs"
    fi
    
    if docker-compose ps fraud-dashboard | grep -q "Up"; then
        echo "📊 Fraud Detection Dashboard: http://localhost:8501"
    fi
    
    if docker-compose ps kafka | grep -q "Up"; then
        echo "📨 Kafka: localhost:9092"
    fi
    
    if docker-compose ps redis | grep -q "Up"; then
        echo "🗄️  Redis: localhost:6379"
    fi
    
    if docker-compose ps postgres | grep -q "Up"; then
        echo "🐘 PostgreSQL: localhost:5432"
    fi
    
    echo
    log "To view logs: docker-compose logs [service-name]"
    log "To stop services: docker-compose down"
    log "To stop and remove volumes: docker-compose down -v"
}

# Cleanup function
cleanup() {
    log "Cleaning up deployment artifacts..."
    
    cd "$PROJECT_ROOT"
    
    # Remove stopped containers
    docker-compose rm -f
    
    # Clean up unused images if requested
    if [[ "$BUILD_FRESH" == "true" ]]; then
        docker image prune -f
    fi
    
    success "Cleanup completed"
}

# Main deployment function
main() {
    echo "🚨 UberEats Fraud Detection System - Deployment"
    echo "================================================"
    echo "Environment: $ENVIRONMENT"
    echo "Services: $SERVICES"
    echo "Build Fresh: $BUILD_FRESH"
    echo "Run Tests: $RUN_TESTS"
    echo "================================================"
    echo
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
        error "Invalid environment: $ENVIRONMENT"
        exit 1
    fi
    
    # Set environment-specific configurations
    export COMPOSE_PROJECT_NAME="fraud-detection-${ENVIRONMENT}"
    
    # Execute deployment steps
    check_dependencies
    validate_environment
    run_tests
    
    # Handle different service deployment scenarios
    if [[ "$SERVICES" == "all" ]] || [[ "$SERVICES" == "infrastructure" ]]; then
        deploy_infrastructure
    fi
    
    if [[ "$SERVICES" != "infrastructure" ]]; then
        build_images
        deploy_application
        wait_for_health
    fi
    
    show_status
    
    success "Deployment completed successfully!"
    
    if [[ "$ENVIRONMENT" == "development" ]]; then
        echo
        log "Development environment is ready!"
        log "You can now:"
        log "  - View the dashboard at http://localhost:8501"
        log "  - Access the API at http://localhost:8000"
        log "  - Send test orders to Kafka topic 'fraud-orders'"
        log "  - Monitor logs with: docker-compose logs -f"
    fi
}

# Trap errors and cleanup
trap 'error "Deployment failed!"; exit 1' ERR

# Parse arguments and run main function
parse_args "$@"
main