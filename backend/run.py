import os
import sys
import uvicorn

# Add project root directory to Python path to resolve imports correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if __name__ == "__main__":
    # Start the backend server on port 8000
    # Enable reloading, watching only the backend/ directory to prevent scanning .venv files
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend"]
    )
