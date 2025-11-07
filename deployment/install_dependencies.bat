@echo off
REM Install dependencies for BodhiRAG deployment

echo ========================================
echo BodhiRAG Dependency Installation
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

echo Installing core dependencies...
echo.

REM Install Hugging Face Hub (required for deployment)
echo [1/5] Installing huggingface_hub...
pip install huggingface_hub

REM Install Gradio (required for interface)
echo [2/5] Installing gradio...
pip install gradio>=4.0.0

REM Install Neo4j driver (optional, for KG)
echo [3/5] Installing neo4j driver...
pip install neo4j>=5.0.0

REM Install ChromaDB (optional, for vector store)
echo [4/5] Installing chromadb...
pip install chromadb==0.4.22

REM Install other dependencies
echo [5/5] Installing other dependencies...
pip install sentence-transformers pydantic python-dotenv langchain==0.0.352

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Optional: Install full requirements
echo   pip install -r requirements.txt
echo.
echo Ready to deploy!
echo   deployment\deploy.bat
echo.

pause
