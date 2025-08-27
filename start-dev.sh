#!/bin/bash

# Claude Conversation Analyzer - Development Server Startup Script
# This starts both the FastAPI backend and React frontend

echo "🚀 Starting Claude Conversation Analyzer..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if npm dependencies are installed
if [ ! -d "web/node_modules" ]; then
    echo "📦 Installing React dependencies..."
    cd web && npm install && cd ..
fi

# Function to cleanup background processes on script exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $API_PID 2>/dev/null
    kill $WEB_PID 2>/dev/null
    exit
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM

echo "🔧 Starting FastAPI backend on http://localhost:8000..."
source venv/bin/activate && python api/main.py &
API_PID=$!

# Give the API server a moment to start
sleep 2

echo "⚛️  Starting React frontend on http://localhost:3000..."
cd web && npm run dev &
WEB_PID=$!
cd ..

echo ""
echo "✅ Both servers are starting up!"
echo ""
echo "📱 Web Interface: http://localhost:3000"
echo "🔗 API Backend:   http://localhost:8000"
echo "📚 API Docs:      http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for both processes
wait $API_PID
wait $WEB_PID