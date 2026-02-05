#!/usr/bin/env python3
"""
Start the Streamlit diagnostic pipeline application
"""
import subprocess
import sys
import os

def main():
    """Start the Streamlit app"""
    print("Starting Diagnostic Pipeline UI...")
    print("App will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Start Streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", "diagnostic_pipeline_ui.py"])

if __name__ == "__main__":
    main()

