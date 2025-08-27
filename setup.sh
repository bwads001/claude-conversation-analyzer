#!/bin/bash

# Claude Conversation Analyzer - Interactive Setup Script
# This script will help you get everything running with minimal effort!

set -e  # Exit on any error

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         Claude Conversation Analyzer - Setup Wizard         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

check_port_available() {
    local port=$1
    # Check if port is in use using ss (netstat alternative)
    if command -v ss >/dev/null 2>&1; then
        ! ss -tulpn | grep -q ":$port "
    else
        # Fallback: try to bind to the port temporarily
        ! (echo >/dev/tcp/localhost/$port) 2>/dev/null
    fi
}

find_available_port() {
    local base_port=$1
    local port=$base_port
    
    while [ $port -lt $((base_port + 100)) ]; do
        if check_port_available $port; then
            echo $port
            return 0
        fi
        port=$((port + 1))
    done
    
    # If we can't find a port in the range, return the base port anyway
    echo $base_port
    return 1
}

# Main setup
clear
print_header

echo "Welcome! This wizard will help you set up the Claude Conversation Analyzer."
echo "It will search and analyze your Claude Code conversation history locally."
echo ""
echo "Press Enter to continue..."
read

# Step 1: Check prerequisites
print_step "Step 1: Checking prerequisites..."
echo ""

# Check Docker
if ! check_command docker; then
    print_error "Docker is required but not installed."
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    echo ""
    echo "After installing Docker, run this script again."
    exit 1
fi

# Check Docker Compose
if ! check_command docker-compose && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is required but not installed."
    echo "It usually comes with Docker Desktop. Please make sure Docker Desktop is properly installed."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is installed but not running."
    echo "Please start Docker Desktop and run this script again."
    exit 1
fi

print_success "All prerequisites are installed!"
echo ""

# Step 2: Check for Ollama
print_step "Step 2: Setting up Ollama for AI embeddings..."
echo ""
echo "Ollama is used to create searchable embeddings of your conversations."
echo "This runs entirely on your local machine - no data is sent anywhere."
echo ""

if check_command ollama; then
    print_success "Ollama is already installed"
    
    # Check if Ollama is running
    if ollama list &> /dev/null; then
        print_success "Ollama is running"
    else
        print_warning "Starting Ollama service..."
        ollama serve &> /dev/null &
        sleep 2
    fi
else
    print_warning "Ollama is not installed."
    echo ""
    echo "Would you like to install Ollama now? (recommended)"
    echo "Note: Ollama runs AI models locally on your computer."
    echo ""
    read -p "Install Ollama? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Detect OS and install Ollama
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            print_step "Installing Ollama for macOS..."
            if command -v brew &> /dev/null; then
                brew install ollama
            else
                curl -fsSL https://ollama.ai/install.sh | sh
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            print_step "Installing Ollama for Linux..."
            curl -fsSL https://ollama.ai/install.sh | sh
        else
            print_error "Automatic installation not available for your OS."
            echo "Please install Ollama manually from: https://ollama.ai/download"
            echo "Then run this script again."
            exit 1
        fi
        
        # Start Ollama
        print_step "Starting Ollama service..."
        ollama serve &> /dev/null &
        sleep 3
    else
        print_warning "Skipping Ollama installation."
        echo "Note: Search functionality will be limited without embeddings."
        echo "You can install Ollama later from: https://ollama.ai/download"
    fi
fi

# Step 3: Pull embedding model
if command -v ollama &> /dev/null; then
    print_step "Step 3: Setting up embedding model..."
    echo ""
    
    # Check if model is already installed
    if ollama list | grep -q "nomic-embed-text"; then
        print_success "Embedding model 'nomic-embed-text' is already installed"
    else
        echo "Downloading embedding model (this may take a few minutes)..."
        echo "This is a one-time download of about 300MB."
        echo ""
        if ollama pull nomic-embed-text; then
            print_success "Embedding model installed successfully!"
        else
            print_warning "Could not install embedding model. You can do this later with:"
            echo "  ollama pull nomic-embed-text"
        fi
    fi
else
    print_step "Step 3: Skipping embedding model (Ollama not available)"
fi

echo ""

# Step 4: Configure environment
print_step "Step 4: Configuring environment..."
echo ""

# Check for port availability and configure accordingly
DB_PORT=$(find_available_port 5432)
API_PORT=$(find_available_port 8000)
WEB_PORT=$(find_available_port 3000)

if [ "$DB_PORT" != "5432" ]; then
    print_warning "Port 5432 is in use, using port $DB_PORT for database"
fi

if [ "$API_PORT" != "8000" ]; then
    print_warning "Port 8000 is in use, using port $API_PORT for API"
fi

if [ "$WEB_PORT" != "3000" ]; then
    print_warning "Port 3000 is in use, using port $WEB_PORT for web interface"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Claude Conversation Analyzer Configuration

# Database settings (no need to change these)
DB_HOST=postgres
DB_PORT=$DB_PORT
DB_NAME=conversations
DB_USER=claude
DB_PASSWORD=claude_analyzer_2024

# Ollama settings
OLLAMA_HOST=host.docker.internal:11434
OLLAMA_MODEL=nomic-embed-text

# API settings
API_HOST=0.0.0.0
API_PORT=$API_PORT

# Frontend settings
VITE_API_URL=http://localhost:$API_PORT

# Port configuration for docker-compose
POSTGRES_PORT=$DB_PORT
BACKEND_PORT=$API_PORT
FRONTEND_PORT=$WEB_PORT
EOF
    print_success "Created .env configuration file"
else
    print_success "Configuration file already exists"
fi

# Step 5: Find Claude conversation files
print_step "Step 5: Locating your Claude conversation files..."
echo ""

# Common locations for Claude files
CLAUDE_PATHS=(
    "$HOME/.claude/projects"
    "$HOME/Documents/Claude/projects"
    "$HOME/Library/Application Support/Claude/projects"
    "$HOME/.config/claude/projects"
)

FOUND_PATH=""
for path in "${CLAUDE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        FOUND_PATH="$path"
        break
    fi
done

if [ -n "$FOUND_PATH" ]; then
    print_success "Found Claude conversations at: $FOUND_PATH"
    echo "export CLAUDE_DATA_PATH=\"$FOUND_PATH\"" >> .env
    
    # Count conversations
    CONV_COUNT=$(find "$FOUND_PATH" -name "*.jsonl" 2>/dev/null | wc -l)
    echo "Found approximately $CONV_COUNT conversation files"
else
    print_warning "Could not automatically find Claude conversation files."
    echo ""
    echo "Please enter the path to your Claude projects folder:"
    echo "(Usually something like: ~/.claude/projects)"
    read -p "Path: " CLAUDE_PATH
    
    if [ -d "$CLAUDE_PATH" ]; then
        echo "export CLAUDE_DATA_PATH=\"$CLAUDE_PATH\"" >> .env
        print_success "Claude data path configured"
    else
        print_warning "Path not found. You'll need to configure this later."
    fi
fi

echo ""

# Step 6: Build and start services
print_step "Step 6: Building and starting services..."
echo ""
echo "This will:"
echo "  1. Start a PostgreSQL database (with pgvector for semantic search)"
echo "  2. Build and start the API server"
echo "  3. Build and start the web interface"
echo ""
echo "First time setup may take 3-5 minutes..."
echo ""

# Stop any existing services
docker-compose -f config/docker-compose.yml down &> /dev/null || true

# Build and start services
if docker-compose -f config/docker-compose.yml up -d --build; then
    print_success "All services started successfully!"
else
    print_error "Failed to start services. Please check the error messages above."
    exit 1
fi

echo ""

# Step 7: Initialize database
print_step "Step 7: Initializing database..."
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for database to be ready..."
sleep 5

# Run database initialization
if docker-compose -f config/docker-compose.yml exec -T api python scripts/init_db.py; then
    print_success "Database initialized successfully!"
else
    print_warning "Database initialization had issues. This might be okay if it's already initialized."
fi

echo ""

# Step 8: Import conversations
print_step "Step 8: Importing your conversations..."
echo ""
echo "This will process your Claude conversation files and make them searchable."
echo "Depending on how many conversations you have, this might take a few minutes."
echo ""
read -p "Import conversations now? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Importing conversations (this may take a while)..."
    if docker-compose -f config/docker-compose.yml exec -T api python scripts/ingest.py --all; then
        print_success "Conversations imported successfully!"
    else
        print_warning "Some conversations may have failed to import. This is usually okay."
    fi
else
    echo "You can import conversations later by running:"
    echo "  docker-compose -f config/docker-compose.yml exec api python scripts/ingest.py --all"
fi

echo ""

# Final step: Success!
print_header
print_success "Setup complete! 🎉"
echo ""
echo "Your Claude Conversation Analyzer is ready to use!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📌 Web Interface: ${GREEN}http://localhost:3000${NC}"
echo "  📌 API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To start using the analyzer:"
echo "  1. Open ${GREEN}http://localhost:3000${NC} in your browser"
echo "  2. Search for topics like 'error handling' or 'React components'"
echo "  3. Click on results to see full conversations"
echo ""
echo "To stop the services:"
echo "  ${YELLOW}docker-compose -f config/docker-compose.yml down${NC}"
echo ""
echo "To start the services again:"
echo "  ${YELLOW}./start.sh${NC}"
echo ""

# Open browser
echo "Would you like to open the web interface now?"
read -p "Open browser? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Detect OS and open browser
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:3000
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open http://localhost:3000 &> /dev/null || echo "Please open http://localhost:3000 in your browser"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        start http://localhost:3000
    else
        echo "Please open http://localhost:3000 in your browser"
    fi
fi

print_success "Enjoy exploring your Claude conversation history!"