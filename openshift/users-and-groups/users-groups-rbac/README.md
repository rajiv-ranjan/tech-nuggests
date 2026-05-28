# OpenShift User Management with htpasswd

This Python script automates the management of OpenShift users using htpasswd authentication.

## Features

- ✅ Check if htpasswd identity provider is configured
- ✅ Auto-configure htpasswd if not present
- ✅ List existing users
- ✅ Add/update users from CSV file
- ✅ Configurable oc CLI path

## Prerequisites

- Python 3.8 or higher
- `oc` CLI tool installed
- `htpasswd` utility installed (part of apache2-utils or httpd-tools)
- OpenShift cluster admin access

### Installing htpasswd

**macOS:**
```bash
brew install httpd
```

**RHEL/CentOS/Fedora:**
```bash
sudo yum install httpd-tools
```

**Ubuntu/Debian:**
```bash
sudo apt-get install apache2-utils
```

## Installation

1. Navigate to the script directory:
```bash
cd /Users/rajranja/Documents/github/rajiv-ranjan/tech-nuggests/openshift/users-and-groups/users-groups-rbac
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the environment:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your oc CLI path
# Find your oc path with: which oc
nano .env
```

4. Ensure you're logged into your OpenShift cluster:
```bash
oc login <cluster-url>
```

## Usage

### 1. Create a Sample CSV File

```bash
python main.py --create-sample-csv
```

This creates `users_sample.csv` with sample users.

### 2. Add Users from CSV

```bash
python main.py --csv users_sample.csv
```

The script will:
- Check if htpasswd is configured
- If not configured, it will configure it automatically
- If configured, it will add/update users from the CSV

### 3. List Existing Users

```bash
python main.py --list-users
```

### 4. Using Custom oc Path

The script reads the oc CLI path from the `.env` file. You can also override it with a command-line argument:

```bash
python main.py --oc-path /custom/path/to/oc --csv users.csv
```

To find your oc path:
```bash
which oc
```

### 5. Enable Debug Logging

Enable DEBUG logging to see detailed information including all oc CLI commands being executed:

```bash
python main.py --log-level DEBUG --csv users.csv
```

Available log levels:
- `DEBUG` - Shows all oc commands, temporary file paths, and detailed operations
- `INFO` - Default level, shows main operations and results
- `WARNING` - Shows warnings only
- `ERROR` - Shows errors only
- `CRITICAL` - Shows critical errors only

## CSV File Format

The CSV file should have two columns: `name` and `password`

Example (`users.csv`):
```csv
name,password
developer1,developer1
developer2,developer2
admin1,admin1
```

**Note:** In production, you should use strong passwords, not the same as usernames!

## Configuration

### Environment Variables (.env file)

The script uses a `.env` file for configuration. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Available configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `OC_CLI_PATH` | Path to oc CLI binary | `/usr/local/bin/oc` |

Example `.env` file:
```bash
# Path to oc CLI
OC_CLI_PATH=/opt/homebrew/bin/oc
```

### Logging

The script uses Python's logging module with configurable log levels:

**Log Levels:**
- `INFO` (default) - Shows main operations, user additions, and results
- `DEBUG` - Shows all oc CLI commands, temporary files, and detailed operations
- `WARNING` - Shows warnings only
- `ERROR` - Shows errors only

**Setting Log Level:**
```bash
# Default INFO level
python main.py --csv users.csv

# Debug level - see all commands
python main.py --log-level DEBUG --csv users.csv

# Error level only
python main.py --log-level ERROR --csv users.csv
```

**Debug Output Example:**
When using `--log-level DEBUG`, you'll see:
- All oc commands being executed
- Command return codes and full output (stdout/stderr)
- Temporary file paths
- OAuth patch content
- htpasswd command executions (with masked passwords)
- Full JSON responses from oc commands

## How It Works

1. **Load Configuration**: Reads the oc CLI path from `.env` file (can be overridden by command-line argument).

2. **Check htpasswd Configuration**: The script checks if htpasswd is configured as an identity provider in the OAuth configuration.

3. **Configure htpasswd (if needed)**:
   - Creates an htpasswd file with initial users
   - Creates a secret in the `openshift-config` namespace
   - Updates the OAuth configuration to use htpasswd

4. **Add/Update Users**:
   - Reads the existing htpasswd secret
   - Adds new users or updates existing ones
   - Updates the secret with the new htpasswd data

## Important Notes

- **First-time setup**: When htpasswd is not configured, the script will configure it with the users from your CSV file.
- **Updates**: When htpasswd is already configured, the script will add new users and update passwords for existing users.
- **Authentication pod restart**: After configuring htpasswd for the first time, it may take a few minutes for the authentication pods to restart.
- **Admin access**: You'll still need to grant appropriate roles/permissions to users separately using `oc adm policy` commands.

## Quick Start Examples

```bash
# Create sample CSV
python main.py --create-sample-csv

# Add users with default (INFO) logging
python main.py --csv users_sample.csv

# Add users with debug logging to see all commands
python main.py --log-level DEBUG --csv users_sample.csv

# List existing users
python main.py --list-users

# Use custom oc path with debug logging
python main.py --oc-path /opt/homebrew/bin/oc --log-level DEBUG --csv users.csv
```

For more detailed examples and output samples, see [EXAMPLES.md](EXAMPLES.md).

### Grant RBAC Permissions

After creating users, grant them appropriate permissions:

**Grant cluster-admin to a user:**
```bash
oc adm policy add-cluster-role-to-user cluster-admin admin1
```

**Grant edit access to a project:**
```bash
oc adm policy add-role-to-user edit developer1 -n my-project
```

**Grant view access to a project:**
```bash
oc adm policy add-role-to-user view viewer1 -n my-project
```

## Troubleshooting

### Error: oc command not found
- Verify the oc CLI path with `which oc`
- Update the `OC_CLI_PATH` in your `.env` file
- Or use the `--oc-path` flag to specify the correct path

### Error: htpasswd command not found
- Install httpd-tools (RHEL) or apache2-utils (Ubuntu)

### Error: Insufficient permissions
- Ensure you're logged in as a cluster admin
- Run `oc whoami` to verify your current user

### Authentication pods not restarting
- Wait a few minutes after initial configuration
- Check pod status: `oc get pods -n openshift-authentication`
- Check OAuth operator: `oc get co authentication`

## Security Best Practices

1. **Use strong passwords**: Don't use username as password in production
2. **Store CSV securely**: Don't commit CSV files with passwords to git
3. **Rotate passwords regularly**: Update the CSV and re-run the script
4. **Use RBAC**: Grant minimum necessary permissions to users
5. **Enable MFA**: Consider using additional identity providers for production

## License

MIT

