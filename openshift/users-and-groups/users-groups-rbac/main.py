#!/usr/bin/env python3
"""
OpenShift User Management Script
Manages users in OpenShift using htpasswd authentication
"""

import subprocess
import json
import csv
import os
import sys
import tempfile
import base64
import logging
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Set up logger
logger = logging.getLogger(__name__)


class OpenShiftUserManager:
    """Manages OpenShift users using htpasswd authentication"""
    
    def __init__(self, oc_path: str = "/usr/local/bin/oc"):
        """
        Initialize the OpenShift User Manager
        
        Args:
            oc_path: Path to the oc CLI binary
        """
        self.oc_path = oc_path
        self.htpasswd_secret_name = "htpass-secret"
        self.oauth_name = "cluster"
        
    def run_oc_command(self, args: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """
        Run an oc command
        
        Args:
            args: List of command arguments
            capture_output: Whether to capture output
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = [self.oc_path] + args
        
        # Log the command being executed at DEBUG level
        logger.debug(f"Executing command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=False
            )
            
            # Log command output at DEBUG level (full output, no truncation)
            if result.returncode == 0:
                logger.debug(f"Command succeeded with return code: {result.returncode}")
                if result.stdout:
                    logger.debug(f"Command stdout:\n{result.stdout}")
            else:
                logger.debug(f"Command failed with return code: {result.returncode}")
                if result.stderr:
                    logger.debug(f"Command stderr:\n{result.stderr}")
            
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            logger.error(f"oc command not found at {self.oc_path}")
            logger.error("Please specify the correct path to oc binary")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error running oc command: {e}")
            return 1, "", str(e)
    
    def check_oc_login(self) -> bool:
        """Check if logged into OpenShift cluster"""
        returncode, stdout, stderr = self.run_oc_command(["whoami"])
        if returncode == 0:
            logger.info(f"✓ Logged in as: {stdout.strip()}")
            return True
        else:
            logger.error("✗ Not logged into OpenShift cluster")
            logger.error("Please run: oc login <cluster-url>")
            return False
    
    def is_htpasswd_configured(self) -> bool:
        """
        Check if htpasswd is configured as an identity provider
        
        Returns:
            True if htpasswd is configured, False otherwise
        """
        logger.info("=== Checking htpasswd configuration ===")
        
        # Get OAuth configuration
        returncode, stdout, stderr = self.run_oc_command([
            "get", "oauth", self.oauth_name, "-o", "json"
        ])
        
        if returncode != 0:
            logger.error(f"✗ Error getting OAuth configuration: {stderr}")
            return False
        
        try:
            oauth_config = json.loads(stdout)
            identity_providers = oauth_config.get("spec", {}).get("identityProviders", [])
            
            for provider in identity_providers:
                if provider.get("type") == "HTPasswd":
                    logger.info(f"✓ htpasswd identity provider found: {provider.get('name')}")
                    return True
            
            logger.warning("✗ htpasswd identity provider not found")
            return False
            
        except json.JSONDecodeError as e:
            logger.error(f"✗ Error parsing OAuth configuration: {e}")
            return False
    
    def create_htpasswd_file(self, users: List[Dict[str, str]]) -> str:
        """
        Create a htpasswd file with users
        
        Args:
            users: List of user dictionaries with 'name' and 'password'
            
        Returns:
            Path to the created htpasswd file
        """
        # Create temporary htpasswd file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.htpasswd')
        htpasswd_path = temp_file.name
        temp_file.close()
        
        logger.debug(f"Created temporary htpasswd file: {htpasswd_path}")
        
        for user in users:
            username = user['name']
            password = user['password']
            
            # Use htpasswd command to add user
            cmd = ['htpasswd', '-bB', htpasswd_path, username, password]
            logger.debug(f"Executing: htpasswd -bB {htpasswd_path} {username} ****")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"✗ Error adding user {username}: {result.stderr}")
            else:
                logger.info(f"  Added user: {username}")
        
        return htpasswd_path
    
    def configure_htpasswd(self, users: List[Dict[str, str]]) -> bool:
        """
        Configure htpasswd authentication for the first time
        
        Args:
            users: List of user dictionaries with 'name' and 'password'
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("=== Configuring htpasswd authentication ===")
        
        # Create htpasswd file
        htpasswd_path = self.create_htpasswd_file(users)
        
        # Create secret in openshift-config namespace
        returncode, stdout, stderr = self.run_oc_command([
            "create", "secret", "generic", self.htpasswd_secret_name,
            "--from-file=htpasswd=" + htpasswd_path,
            "-n", "openshift-config"
        ])
        
        # Clean up temp file
        os.unlink(htpasswd_path)
        logger.debug(f"Cleaned up temporary file: {htpasswd_path}")
        
        if returncode != 0:
            logger.error(f"✗ Error creating secret: {stderr}")
            return False
        
        logger.info(f"✓ Created secret: {self.htpasswd_secret_name}")
        
        # Update OAuth configuration
        oauth_patch = {
            "spec": {
                "identityProviders": [
                    {
                        "name": "htpasswd_provider",
                        "mappingMethod": "claim",
                        "type": "HTPasswd",
                        "htpasswd": {
                            "fileData": {
                                "name": self.htpasswd_secret_name
                            }
                        }
                    }
                ]
            }
        }
        
        logger.debug(f"OAuth patch: {json.dumps(oauth_patch, indent=2)}")
        
        returncode, stdout, stderr = self.run_oc_command([
            "patch", "oauth", self.oauth_name,
            "--type=merge",
            "--patch", json.dumps(oauth_patch)
        ])
        
        if returncode != 0:
            logger.error(f"✗ Error updating OAuth configuration: {stderr}")
            return False
        
        logger.info("✓ OAuth configuration updated")
        logger.info("Note: It may take a few minutes for the authentication pods to restart")
        return True
    
    def get_existing_users(self) -> List[str]:
        """
        Get list of existing htpasswd users
        
        Returns:
            List of usernames
        """
        logger.info("=== Getting existing users ===")
        
        # Get the htpasswd secret
        returncode, stdout, stderr = self.run_oc_command([
            "get", "secret", self.htpasswd_secret_name,
            "-n", "openshift-config",
            "-o", "json"
        ])
        
        if returncode != 0:
            logger.error(f"✗ Error getting secret: {stderr}")
            return []
        
        try:
            secret = json.loads(stdout)
            htpasswd_data = secret.get("data", {}).get("htpasswd", "")
            
            if not htpasswd_data:
                logger.warning("✗ No htpasswd data found in secret")
                return []
            
            # Decode base64 htpasswd data
            htpasswd_content = base64.b64decode(htpasswd_data).decode('utf-8')
            logger.debug(f"Decoded htpasswd content length: {len(htpasswd_content)} bytes")
            
            # Extract usernames (first part before ':')
            users = [line.split(':')[0] for line in htpasswd_content.strip().split('\n') if line]
            
            logger.info(f"✓ Found {len(users)} existing users:")
            for user in users:
                logger.info(f"  - {user}")
            
            return users
            
        except Exception as e:
            logger.error(f"✗ Error parsing secret: {e}")
            return []
    
    def add_users_from_csv(self, csv_path: str) -> bool:
        """
        Add users from a CSV file
        
        Args:
            csv_path: Path to CSV file with 'name' and 'password' columns
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"=== Adding users from CSV: {csv_path} ===")
        
        # Read CSV file
        if not os.path.exists(csv_path):
            logger.error(f"✗ CSV file not found: {csv_path}")
            return False
        
        users = []
        try:
            with open(csv_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'name' not in row or 'password' not in row:
                        logger.error("✗ CSV must have 'name' and 'password' columns")
                        return False
                    users.append({
                        'name': row['name'].strip(),
                        'password': row['password'].strip()
                    })
            
            logger.info(f"✓ Read {len(users)} users from CSV")
            logger.debug(f"Users to process: {[u['name'] for u in users]}")
            
        except Exception as e:
            logger.error(f"✗ Error reading CSV file: {e}")
            return False
        
        if not users:
            logger.warning("✗ No users found in CSV file")
            return False
        
        # Get existing users
        existing_users = self.get_existing_users()
        
        # Create temporary htpasswd file with existing + new users
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.htpasswd')
        htpasswd_path = temp_file.name
        temp_file.close()
        
        logger.debug(f"Created temporary htpasswd file: {htpasswd_path}")
        
        # If there are existing users, get the current htpasswd file
        if existing_users:
            returncode, stdout, stderr = self.run_oc_command([
                "extract", "secret/" + self.htpasswd_secret_name,
                "-n", "openshift-config",
                "--to=-",
                "--confirm"
            ])
            
            if returncode == 0:
                with open(htpasswd_path, 'w') as f:
                    f.write(stdout)
                logger.debug("Extracted existing htpasswd data")
        
        # Add new users
        new_users_count = 0
        updated_users_count = 0
        
        for user in users:
            username = user['name']
            password = user['password']
            
            if username in existing_users:
                logger.info(f"  Updating user: {username}")
                # Remove old entry first
                cmd = ['htpasswd', '-D', htpasswd_path, username]
                logger.debug(f"Executing: {' '.join(cmd)}")
                subprocess.run(cmd, capture_output=True)
                updated_users_count += 1
            else:
                logger.info(f"  Adding new user: {username}")
                new_users_count += 1
            
            # Add user
            cmd = ['htpasswd', '-bB', htpasswd_path, username, password]
            logger.debug(f"Executing: htpasswd -bB {htpasswd_path} {username} ****")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"✗ Error adding user {username}: {result.stderr}")
        
        # Update the secret
        returncode, stdout, stderr = self.run_oc_command([
            "set", "data", "secret/" + self.htpasswd_secret_name,
            "-n", "openshift-config",
            "--from-file=htpasswd=" + htpasswd_path
        ])
        
        # Clean up temp file
        os.unlink(htpasswd_path)
        logger.debug(f"Cleaned up temporary file: {htpasswd_path}")
        
        if returncode != 0:
            logger.error(f"✗ Error updating secret: {stderr}")
            return False
        
        logger.info(f"✓ Successfully processed {len(users)} users")
        logger.info(f"  - New users added: {new_users_count}")
        logger.info(f"  - Existing users updated: {updated_users_count}")
        
        return True


def create_sample_csv(output_path: str = "users_sample.csv"):
    """
    Create a sample CSV file with users
    
    Args:
        output_path: Path to output CSV file
    """
    sample_users = [
        {"name": "developer1", "password": "developer1"},
        {"name": "developer2", "password": "developer2"},
        {"name": "admin1", "password": "admin1"},
        {"name": "viewer1", "password": "viewer1"},
        {"name": "operator1", "password": "operator1"},
    ]
    
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['name', 'password']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for user in sample_users:
            writer.writerow(user)
    
    logger.info(f"✓ Created sample CSV file: {output_path}")


def main():
    """Main function"""
    import argparse
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get oc path from environment variable or use default
    default_oc_path = os.getenv('OC_CLI_PATH', '/usr/local/bin/oc')
    
    parser = argparse.ArgumentParser(
        description='OpenShift User Management with htpasswd',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a sample CSV file
  python main.py --create-sample-csv
  
  # Add users from CSV (auto-configure htpasswd if needed)
  python main.py --csv users_sample.csv
  
  # List existing users
  python main.py --list-users
  
  # Enable debug logging to see oc commands
  python main.py --log-level DEBUG --csv users.csv
  
  # Specify custom oc path (overrides .env file)
  python main.py --oc-path /custom/path/to/oc --csv users.csv

Configuration:
  The script reads the oc CLI path from .env file (OC_CLI_PATH variable).
  You can override this with the --oc-path command line argument.
        """
    )
    
    parser.add_argument(
        '--oc-path',
        default=default_oc_path,
        help=f'Path to oc CLI binary (default from .env: {default_oc_path})'
    )
    parser.add_argument(
        '--csv',
        help='Path to CSV file with users (columns: name, password)'
    )
    parser.add_argument(
        '--create-sample-csv',
        action='store_true',
        help='Create a sample CSV file'
    )
    parser.add_argument(
        '--list-users',
        action='store_true',
        help='List existing htpasswd users'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level (default: INFO). Use DEBUG to see oc CLI commands.'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logger.debug(f"Logging level set to: {args.log_level}")
    logger.debug(f"oc CLI path: {args.oc_path}")
    
    # Create sample CSV if requested
    if args.create_sample_csv:
        create_sample_csv()
        return
    
    # Initialize manager
    manager = OpenShiftUserManager(oc_path=args.oc_path)
    
    # Check if logged in
    if not manager.check_oc_login():
        sys.exit(1)
    
    # List users if requested
    if args.list_users:
        if manager.is_htpasswd_configured():
            manager.get_existing_users()
        else:
            logger.warning("htpasswd is not configured yet")
        return
    
    # Add users from CSV
    if args.csv:
        # Check if htpasswd is configured
        if not manager.is_htpasswd_configured():
            logger.info("htpasswd is not configured. Configuring now...")
            
            # Read users from CSV for initial configuration
            users = []
            try:
                with open(args.csv, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        users.append({
                            'name': row['name'].strip(),
                            'password': row['password'].strip()
                        })
            except Exception as e:
                logger.error(f"✗ Error reading CSV file: {e}")
                sys.exit(1)
            
            if manager.configure_htpasswd(users):
                logger.info("✓ htpasswd configured successfully")
            else:
                logger.error("✗ Failed to configure htpasswd")
                sys.exit(1)
        else:
            # htpasswd already configured, add users
            if manager.add_users_from_csv(args.csv):
                logger.info("✓ Users added/updated successfully")
            else:
                logger.error("✗ Failed to add users")
                sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
