@echo off
REM Quick deployment script for BodhiRAG to Hugging Face

echo ========================================
echo BodhiRAG Hugging Face Deployment
echo ========================================
echo.

REM Check if HF_TOKEN is set
if "%HF_TOKEN%"=="" (
    echo ERROR: HF_TOKEN environment variable not set
    echo.
    echo Please set your Hugging Face token:
    echo   set HF_TOKEN=hf_your_token_here
    echo.
    echo Get your token from: https://huggingface.co/settings/tokens
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.11 or higher
    exit /b 1
)

REM Install huggingface_hub if not present
echo Installing dependencies...
pip install huggingface_hub --quiet

REM Get repo name from user or use default
set /p REPO_NAME="Enter Space name (default: bodhirag-space-biology): "
if "%REPO_NAME%"=="" set REPO_NAME=bodhirag-space-biology

echo.
echo Deploying to: %REPO_NAME%
echo.

REM Run deployment script
python deployment\huggingface_deploy.py --token %HF_TOKEN% --repo-name %REPO_NAME%

if errorlevel 1 (
    echo.
    echo Deployment failed!
    exit /b 1
)

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Your Space: https://huggingface.co/spaces/EricSiq/BodhiRAG
echo.
echo Next steps:
echo 1. Go to Space settings
echo 2. Add environment variables:
echo    - NEO4J_URI
echo    - NEO4J_USERNAME
echo    - NEO4J_PASSWORD
echo 3. Wait for build to complete
echo 4. Test your model!
echo.

pause
