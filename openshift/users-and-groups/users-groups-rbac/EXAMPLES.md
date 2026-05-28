# Usage Examples

## Basic Operations

### 1. Create Sample CSV File

```bash
python main.py --create-sample-csv
```

**Output:**
```
INFO: ✓ Created sample CSV file: users_sample.csv
```

### 2. Add Users with Default (INFO) Logging

```bash
python main.py --csv users_sample.csv
```

**Output:**
```
INFO: ✓ Logged in as: admin
INFO: === Checking htpasswd configuration ===
INFO: ✓ htpasswd identity provider found: htpasswd_provider
INFO: === Adding users from CSV: users_sample.csv ===
INFO: ✓ Read 5 users from CSV
INFO: === Getting existing users ===
INFO: ✓ Found 2 existing users:
INFO:   - developer1
INFO:   - admin1
INFO:   Updating user: developer1
INFO:   Adding new user: developer2
INFO:   Updating user: admin1
INFO:   Adding new user: viewer1
INFO:   Adding new user: operator1
INFO: ✓ Successfully processed 5 users
INFO:   - New users added: 3
INFO:   - Existing users updated: 2
INFO: ✓ Users added/updated successfully
```

### 3. Add Users with DEBUG Logging

```bash
python main.py --log-level DEBUG --csv users_sample.csv
```

**Output:**
```
DEBUG: Logging level set to: DEBUG
DEBUG: oc CLI path: /usr/local/bin/oc
DEBUG: Executing command: /usr/local/bin/oc whoami
DEBUG: Command succeeded with return code: 0
DEBUG: Command stdout:
system:admin
INFO: ✓ Logged in as: system:admin
INFO: === Checking htpasswd configuration ===
DEBUG: Executing command: /usr/local/bin/oc get oauth cluster -o json
DEBUG: Command succeeded with return code: 0
DEBUG: Command stdout:
{
  "apiVersion": "config.openshift.io/v1",
  "kind": "OAuth",
  "metadata": {
    "name": "cluster"
  },
  "spec": {
    "identityProviders": [
      {
        "name": "htpasswd_provider",
        "type": "HTPasswd",
        "htpasswd": {
          "fileData": {
            "name": "htpass-secret"
          }
        }
      }
    ]
  }
}
INFO: ✓ htpasswd identity provider found: htpasswd_provider
INFO: === Adding users from CSV: users_sample.csv ===
INFO: ✓ Read 5 users from CSV
DEBUG: Users to process: ['developer1', 'developer2', 'admin1', 'viewer1', 'operator1']
INFO: === Getting existing users ===
DEBUG: Executing command: /usr/local/bin/oc get secret htpass-secret -n openshift-config -o json
DEBUG: Command succeeded with return code: 0
DEBUG: Decoded htpasswd content length: 450 bytes
INFO: ✓ Found 2 existing users:
INFO:   - developer1
INFO:   - admin1
DEBUG: Created temporary htpasswd file: /tmp/tmpxyz123.htpasswd
DEBUG: Executing command: /usr/local/bin/oc extract secret/htpass-secret -n openshift-config --to=- --confirm
DEBUG: Command succeeded with return code: 0
DEBUG: Extracted existing htpasswd data
INFO:   Updating user: developer1
DEBUG: Executing: htpasswd -D /tmp/tmpxyz123.htpasswd developer1
DEBUG: Executing: htpasswd -bB /tmp/tmpxyz123.htpasswd developer1 ****
INFO:   Adding new user: developer2
DEBUG: Executing: htpasswd -bB /tmp/tmpxyz123.htpasswd developer2 ****
INFO:   Updating user: admin1
DEBUG: Executing: htpasswd -D /tmp/tmpxyz123.htpasswd admin1
DEBUG: Executing: htpasswd -bB /tmp/tmpxyz123.htpasswd admin1 ****
INFO:   Adding new user: viewer1
DEBUG: Executing: htpasswd -bB /tmp/tmpxyz123.htpasswd viewer1 ****
INFO:   Adding new user: operator1
DEBUG: Executing: htpasswd -bB /tmp/tmpxyz123.htpasswd operator1 ****
DEBUG: Executing command: /usr/local/bin/oc set data secret/htpass-secret -n openshift-config --from-file=htpasswd=/tmp/tmpxyz123.htpasswd
DEBUG: Command succeeded with return code: 0
DEBUG: Cleaned up temporary file: /tmp/tmpxyz123.htpasswd
INFO: ✓ Successfully processed 5 users
INFO:   - New users added: 3
INFO:   - Existing users updated: 2
INFO: ✓ Users added/updated successfully
```

### 4. List Existing Users

```bash
python main.py --list-users
```

**Output:**
```
INFO: ✓ Logged in as: admin
INFO: === Checking htpasswd configuration ===
INFO: ✓ htpasswd identity provider found: htpasswd_provider
INFO: === Getting existing users ===
INFO: ✓ Found 5 existing users:
INFO:   - developer1
INFO:   - developer2
INFO:   - admin1
INFO:   - viewer1
INFO:   - operator1
```

### 5. First-Time htpasswd Configuration

```bash
python main.py --csv users_sample.csv
```

**Output (when htpasswd is not configured):**
```
INFO: ✓ Logged in as: admin
INFO: === Checking htpasswd configuration ===
WARNING: ✗ htpasswd identity provider not found
INFO: htpasswd is not configured. Configuring now...
INFO: === Configuring htpasswd authentication ===
INFO:   Added user: developer1
INFO:   Added user: developer2
INFO:   Added user: admin1
INFO:   Added user: viewer1
INFO:   Added user: operator1
INFO: ✓ Created secret: htpass-secret
INFO: ✓ OAuth configuration updated
INFO: Note: It may take a few minutes for the authentication pods to restart
INFO: ✓ htpasswd configured successfully
```

## Advanced Usage

### Custom oc CLI Path

```bash
python main.py --oc-path /opt/homebrew/bin/oc --csv users.csv
```

### Debug with Custom Path

```bash
python main.py --oc-path /custom/path/oc --log-level DEBUG --csv users.csv
```

### Error Logging Only

```bash
python main.py --log-level ERROR --csv users.csv
```

## Troubleshooting Examples

### Not Logged In

```bash
python main.py --list-users
```

**Output:**
```
ERROR: ✗ Not logged into OpenShift cluster
ERROR: Please run: oc login <cluster-url>
```

### Invalid CSV Format

```bash
python main.py --csv invalid.csv
```

**Output:**
```
INFO: ✓ Logged in as: admin
INFO: === Checking htpasswd configuration ===
INFO: ✓ htpasswd identity provider found: htpasswd_provider
INFO: === Adding users from CSV: invalid.csv ===
ERROR: ✗ CSV must have 'name' and 'password' columns
ERROR: ✗ Failed to add users
```

### File Not Found

```bash
python main.py --csv nonexistent.csv
```

**Output:**
```
INFO: ✓ Logged in as: admin
INFO: === Checking htpasswd configuration ===
INFO: ✓ htpasswd identity provider found: htpasswd_provider
INFO: === Adding users from CSV: nonexistent.csv ===
ERROR: ✗ CSV file not found: nonexistent.csv
ERROR: ✗ Failed to add users
```

### Wrong oc Path

```bash
python main.py --oc-path /wrong/path/oc --list-users
```

**Output:**
```
ERROR: oc command not found at /wrong/path/oc
ERROR: Please specify the correct path to oc binary
```

## Log Level Comparison

### INFO Level (Default)
- Shows: Main operations, user additions, results
- Use when: Normal operation, production use

### DEBUG Level
- Shows: All oc commands, temp files, detailed operations
- Use when: Troubleshooting, development, understanding what the script does

### WARNING Level
- Shows: Warnings and above
- Use when: You only care about potential issues

### ERROR Level
- Shows: Errors only
- Use when: Silent operation, only show failures

## Complete Workflow Example

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env to set OC_CLI_PATH

# 3. Login to OpenShift
oc login https://api.cluster.example.com:6443

# 4. Create sample CSV (or prepare your own)
python main.py --create-sample-csv

# 5. Add users with debug logging (first time)
python main.py --log-level DEBUG --csv users_sample.csv

# 6. Verify users were added
python main.py --list-users

# 7. Grant permissions to users
oc adm policy add-cluster-role-to-user cluster-admin admin1
oc adm policy add-role-to-user edit developer1 -n my-project
oc adm policy add-role-to-user edit developer2 -n my-project
oc adm policy add-role-to-user view viewer1 -n my-project

# 8. Test user login
oc login https://api.cluster.example.com:6443 -u developer1 -p developer1
oc whoami

# 9. Update user passwords (prepare updated CSV)
python main.py --csv users_updated.csv
```

