# Python Environment Troubleshooting for RAG Systems

## Problem
When working with Python packages (especially PyMuPDF/pymupdf) in RAG systems, you may encounter module import errors despite the package appearing installed.

## Root Cause
The active Python environment (venv) differs from the system Python where packages are installed. This creates a mismatch where libraries are installed in user site-packages but the venv doesn't have them.

## Solutions

### 1. Use System Python Explicitly
```bash
# Find correct Python installation (system vs venv)
ls /c/Python3*.exe
which python3  # Shows venv path

# Use system Python with explicit package path
C:/Python314/python.exe your_script.py
```

### 2. Set PYTHONPATH
```bash
# Prepend site-packages to Python path
PYTHONPATH="/c/Users/Milos/AppData/Roaming/Python/Python314/site-packages" python3 your_script.py
```

### 3. Use Script File (Avoid Escaping Issues)
When dealing with Windows paths in Python scripts executed from bash:
```python
# GOOD - Use raw strings
path = r'C:\Users\Milos\AppData\Roaming\Python\Python314\site-packages'

# BAD - Causes UnicodeDecodeError
path = 'C:\\Users\\Milos\\AppData\Roaming\\...'  # Broken backslashes

# GOOD - Use forward slashes (bash compatible)
path = '/c/Users/Milos/AppData/Roaming/Python/Python314/site-packages'
```

## File Naming Convention for DOI-Safe Filenames
When working with DOI-based filenames for RAG indexing:
```python
# Only replace forward slashes, keep dots
doi_safe = doi.replace('/', '_')  # "10.1038/s41598..." → "10.1038_s41598..."

# NOT this (incorrectly replaces dots, breaking file matching):
doi_safe = doi.replace('/', '_').replace('.', '_')  # Wrong!
```

## Debug Pattern for "Files Not Found" Issues
When files seem to exist but aren't found by your script:
1. Check actual working directory: `python3 -c "import os; print(os.getcwd())"`
2. Verify path resolution: `python3 -c "import os; print(os.path.exists(path))"`
3. Use absolute paths in scripts: `base_dir = r'C:\full\path\to\directory'`
4. Verify filename conventions match exactly (especially DOI-safe naming)