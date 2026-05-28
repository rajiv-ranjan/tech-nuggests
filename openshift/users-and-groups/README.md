# Use Cases

## Add users and groups

### OpenShift User Management with htpasswd

A Python script that automates user management in OpenShift using htpasswd authentication.

**Location:** `users-groups-rbac/`

**Features:**
- ✅ Auto-configure htpasswd identity provider
- ✅ Add/update users from CSV file
- ✅ List existing users
- ✅ Support for custom oc CLI path

**Quick Start:**
```bash
cd users-groups-rbac
python main.py --create-sample-csv
python main.py --csv users_sample.csv
```

See [users-groups-rbac/README.md](users-groups-rbac/README.md) for detailed documentation.

