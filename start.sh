#!/bin/bash

# Claude Conversation Analyzer - Simple Startup Script
# Use this after running setup.sh to start all services

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         Claude Conversation Analyzer - Starting...          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

clear
print_header

# Check if setup was run
if [ ! -f .env ]; then
    echo "⚠️  Setup has not been completed yet."
    echo ""
    echo "Please run the setup script first:"
    echo "  ${GREEN}./setup.sh${NC}"
    echo ""
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running."
    echo ""
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default ports if not specified
FRONTEND_PORT=${FRONTEND_PORT:-3000}
BACKEND_PORT=${BACKEND_PORT:-8000}

# Start services
print_step "Starting all services..."
echo ""
echo "This will start:"
echo "  🗄️  PostgreSQL database with pgvector"
echo "  🔧 FastAPI backend server"
echo "  🌐 React web interface"
echo ""

# Stop any existing services
docker-compose -f config/docker-compose.yml down &> /dev/null

# Start services with live output
if docker-compose -f config/docker-compose.yml up -d; then
    echo ""
    print_success "All services started successfully!"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  🌐 Web Interface: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
    echo "  📋 API Documentation: ${GREEN}http://localhost:$BACKEND_PORT/docs${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Wait for services to be healthy
    print_step "Waiting for services to be ready..."
    
    # Check database health
    for i in {1..30}; do
        if docker-compose -f config/docker-compose.yml exec -T postgres pg_isready -U claude -d conversations &> /dev/null; then
            print_success "Database is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Database is taking longer than expected to start"
        fi
        sleep 1
    done
    
    # Check API health
    for i in {1..60}; do
        if curl -f http://localhost:$BACKEND_PORT/api/health &> /dev/null; then
            print_success "API server is ready"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "API server is taking longer than expected to start"
        fi
        sleep 1
    done
    
    # Check web interface
    for i in {1..30}; do
        if curl -f http://localhost:$FRONTEND_PORT &> /dev/null; then
            print_success "Web interface is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Web interface is taking longer than expected to start"
        fi
        sleep 1
    done
    
    echo ""
    print_success "🎉 Claude Conversation Analyzer is ready!"
    echo ""
    echo "Open ${GREEN}http://localhost:$FRONTEND_PORT${NC} in your browser to start searching your conversations."
    echo ""
    echo "To stop the services, press Ctrl+C or run:"
    echo "  ${YELLOW}docker-compose -f config/docker-compose.yml down${NC}"
    echo ""
    
    # Ask if user wants to open browser
    read -p "Open web interface in browser? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Detect OS and open browser
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open http://localhost:$FRONTEND_PORT
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open http://localhost:$FRONTEND_PORT &> /dev/null || echo "Please open http://localhost:$FRONTEND_PORT in your browser"
        elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            start http://localhost:$FRONTEND_PORT
        else
            echo "Please open http://localhost:$FRONTEND_PORT in your browser"
        fi
    fi
    
    # Show logs option
    echo ""
    echo "To view service logs:"
    echo "  ${YELLOW}docker-compose -f config/docker-compose.yml logs -f${NC}"
    
else
    echo ""
    echo "❌ Failed to start services. Please check the error messages above."
    echo ""
    echo "Common solutions:"
    echo "  • Make sure Docker Desktop is running"
    echo "  • Check that ports 3000, 8000, and 5432 are not in use"
    echo "  • Try running: docker-compose -f config/docker-compose.yml down && docker-compose -f config/docker-compose.yml up -d --build"
    echo ""
    exit 1
fi