# Changelog

All notable changes to the OpenShift User Management script.

## [0.2.1] - 2025-12-01

### Changed
- Removed truncation of debug output - full stdout/stderr now logged
- Command output now displayed with newlines for better readability
- Enhanced debugging experience with complete command responses

## [0.2.0] - 2025-12-01

### Added
- **Logging System**: Replaced all `print()` statements with Python's `logging` module
  - Configurable log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - Default log level: INFO
  - New `--log-level` command-line argument
  
- **Debug Logging Features**:
  - All oc CLI commands are logged at DEBUG level
  - Command return codes and output logged
  - Temporary file paths logged
  - htpasswd commands logged (with password masking)
  - OAuth patch content logged
  - CSV parsing details logged
  
- **Documentation**:
  - Added EXAMPLES.md with comprehensive usage examples
  - Added CHANGELOG.md to track changes
  - Updated README.md with logging section
  - Documented log levels and their use cases

### Changed
- `print()` → `logger.info()` for normal operations
- `print()` → `logger.error()` for errors
- `print()` → `logger.warning()` for warnings
- `print()` → `logger.debug()` for detailed debugging information
- Improved command execution logging in `run_oc_command()` method
- Enhanced error messages with appropriate log levels

### Technical Details
- Added `import logging` to imports
- Created module-level logger: `logger = logging.getLogger(__name__)`
- Configured logging in `main()` function with:
  - Format: `'%(levelname)s: %(message)s'`
  - Handler: `logging.StreamHandler(sys.stdout)`
  - Dynamic level based on `--log-level` argument

## [0.1.0] - 2025-12-01

### Added
- **Environment Configuration**: Support for `.env` file to configure oc CLI path
  - Added `python-dotenv` dependency
  - Created `.env.example` template file
  - Created default `.env` file
  - Updated `.gitignore` to exclude `.env` from version control
  
- **Environment Variables**:
  - `OC_CLI_PATH`: Configurable path to oc CLI binary
  - Fallback to `/usr/local/bin/oc` if not set
  - Command-line `--oc-path` argument overrides env file

### Changed
- Updated `requirements.txt` to include `python-dotenv==1.0.0`
- Updated `pyproject.toml` with `python-dotenv>=1.0.0` dependency
- Modified `main()` function to load environment variables
- Updated README.md with environment configuration instructions

## [0.0.1] - Initial Release

### Features
- OpenShift user management with htpasswd authentication
- Auto-detect htpasswd configuration
- Auto-configure htpasswd if not present
- Add/update users from CSV file
- List existing users
- Sample CSV generation
- Comprehensive README with installation and usage instructions

