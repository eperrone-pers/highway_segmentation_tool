# Highway Segmentation GA - Environment Setup

## Quick Setup Instructions

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Activate virtual environment (Mac/Linux)  
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Or install with development dependencies
pip install -e .
```

### 3. Verify Installation

```bash
# Run the default test suite (excludes performance tests)
python run_tests.py

# Regression gate used during development
python -m pytest tests/regression -q

# Or run specific test
python -m pytest tests/test_simple_controller.py -v
```

### 4. Run the Application

```bash
# Run GUI application
python src/gui_main.py

# Run command line version
python src/run.py
```

## Python Version Requirements

- Python 3.8 or higher
- See `requirements.txt` for all package dependencies
- See `pyproject.toml` for project configuration

## Included in this Package

- ✅ Complete source code (src/)
- ✅ All tests (tests/)
- ✅ Documentation (README.md, docs/, USER_GUIDE.md)
- ✅ Requirements files (requirements.txt, pyproject.toml)
- ✅ Sample data files (data/)
- ✅ Test runner (run_tests.py)

## Notes

- Virtual environment excluded (recreate using instructions above)
- User settings file (`src/app_settings.json`) is generated locally by the app and is git-ignored
- Output directories (Results/, test_results/) are generated outputs and are git-ignored
- IDE settings (.vscode/) excluded (personal configuration)
- The refactoring tracker/plans (refactoring/) are developer-only notes and are not required to run the tool

## Regenerating the Delivery Zip

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_deliverable.ps1
```

Optional switches:

- Include refactoring notes: `-IncludeRefactoring`

Created: April 14, 2026
