# This script creates and activates the virtual environment, 
# and installs all project dependencies.

# 1. Define Environment Name
VENV_NAME="venv"

# 2. Create the Virtual Environment using the specified Python interpreter (using py for Windows compatibility)
echo "Creating virtual environment: $VENV_NAME"
# Attempt to use python3, falling back to python
python3 -m venv $VENV_NAME || python -m venv $VENV_NAME

# 3. Activate the environment (Cross-platform activation instruction)
echo "Activating virtual environment..."
# Check if the bin folder exists (Linux/Mac)
if [ -d "$VENV_NAME/bin" ]; then
    source $VENV_NAME/bin/activate
# Check if the Scripts folder exists (Windows)
elif [ -d "$VENV_NAME/Scripts" ]; then
    # Note: 'source' command is not available on Windows Command Prompt/PowerShell. 
    # Users must execute this line manually in their shell:
    echo "Windows users: Please run '$VENV_NAME\Scripts\activate' manually."
else
    echo "Could not find standard virtual environment folders."
    exit 1
fi

# 4. Install all dependencies from requirements.txt
echo "Installing core dependencies..."
pip install -r requirements.txt

# 5. Install the required spaCy language model data
# This step is crucial and must be run *after* spaCy itself is installed.
echo "Installing spaCy language model..."
python -m spacy download en_core_web_lg

echo "SETUP COMPLETE."
echo "You are now inside the '$VENV_NAME' environment."
echo "You can now run 'python scripts/run_pipeline.py'"


