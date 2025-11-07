@echo off
echo Creating virtual environment...
py -3.11 -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel

echo Installing requirements...
pip install -r requirements.txt

echo Installing spaCy model...
python -m spacy download en_core_web_lg
python -m spacy download en_core_web_sm

echo.
echo SETUP COMPLETE
echo To activate later, run: venv\Scripts\activate
