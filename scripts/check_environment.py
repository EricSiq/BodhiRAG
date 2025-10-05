
"""
Environment Check Script
Validates all dependencies and configurations before running the pipeline
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_python_environment():
    """Check Python version and critical packages"""
    print("Checking Python Environment...")
    
    # Python version
    python_version = sys.version_info
    print(f"   Python: {sys.version}")
    if python_version < (3, 8):
        print("   Python 3.8+ required")
        return False
    else:
        print("   Python version OK")
    
    # Critical packages
    critical_packages = [
        'pandas', 'neo4j', 'chromadb', 'plotly', 'dash',
        'langchain_core', 'pydantic', 'transformers'
    ]
    
    missing_packages = []
    for package in critical_packages:
        try:
            __import__(package)
            print(f"   {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"   {package}")
    
    if missing_packages:
        print(f"   Missing packages: {missing_packages}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def check_environment_variables():
    """Check required environment variables"""
    print("\n🔍 Checking Environment Variables...")
    
    required_vars = {
        'NEO4J_URI': 'bolt://localhost:7687',
        'NEO4J_USERNAME': 'neo4j', 
        'NEO4J_PASSWORD': 'password'
    }
    
    all_set = True
    for var, default in required_vars.items():
        value = os.getenv(var, default)
        if value == default and var == 'NEO4J_PASSWORD':
            print(f"   {var}: Using default - change in production")
        else:
            print(f"   {var}: Set")
    
    return all_set

def check_data_files():
    """Check required data files exist"""
    print("\nChecking Data Files...")
    
    data_dir = project_root / 'data'
    required_files = [
        data_dir / 'SB_publication_PMC.csv'
    ]
    
    all_exist = True
    for file_path in required_files:
        if file_path.exists():
            print(f"   {file_path.name}")
        else:
            print(f"   ❌ {file_path.name} - Not found")
            all_exist = False
    
    # Create processed directory if it doesn't exist
    processed_dir = data_dir / 'processed'
    processed_dir.mkdir(exist_ok=True)
    print(f"   processed/ directory ready")
    
    return all_exist

def main():
    print("BodhiRAG Environment Check")
    print("=" * 50)
    
    checks = [
        check_python_environment(),
        check_environment_variables(), 
        check_data_files()
    ]
    
    print("\n" + "=" * 50)
    if all(checks):
        print("All environment checks passed!")
        print("   Next steps:")
        print("   1. Run: python scripts/setup_db.py")
        print("   2. Run: python scripts/run_pipeline.py")
    else:
        print("Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()