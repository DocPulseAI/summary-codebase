import os
import re
import requests
import subprocess
import tempfile
from typing import List, Dict, Optional, Tuple
from src.config import config
from src.utils import logger, get_retry_decorator

retry_api = get_retry_decorator()

class GitHubClient:
    def __init__(self, repo_owner: str, repo_name: str, token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self._setup_git_credentials()
        

    def _sanitize_log(self, text: str) -> str:
        """Remove tokens and credentials from log output."""
        if not text:
            return text
        # Redact tokens in URLs
        text = re.sub(r'://[^@:]+:[^@]+@', '://***@', text)
        text = re.sub(r'://x-access-token:[^@]+@', '://***@', text)
        # Redact token-like strings (ghp_ for personal access tokens, gho_ for OAuth tokens)
        text = re.sub(r'ghp_[a-zA-Z0-9_]+', '***REDACTED_TOKEN***', text)
        text = re.sub(r'gho_[a-zA-Z0-9_]+', '***REDACTED_TOKEN***', text)
        return text

    def _setup_git_credentials(self):
        """Setup secure Git authentication using credential helper."""
        # Create a temporary credential helper script
        self.credential_helper = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.sh'
        )
        self.credential_helper.write(f'''#!/bin/sh
echo "username=x-access-token"
echo "password={self.token}"
''')
        self.credential_helper.flush()
        self.credential_helper.close()  # Close file handle
        os.chmod(self.credential_helper.name, 0o700)

        # Configure git to use the credential helper
        self._run_git_command(
            ["config", "--local", "credential.helper", f"!{self.credential_helper.name}"],
            check=False
        )
        
        # Register cleanup
        import atexit
        atexit.register(self.cleanup)

    def cleanup(self):
        """Remove temporary credential helper file."""
        if hasattr(self, 'credential_helper') and os.path.exists(self.credential_helper.name):
            try:
                os.unlink(self.credential_helper.name)
            except OSError:
                pass

    def _run_git_command(self, args: List[str], check=True):
        # Sanitize command for logging (remove sensitive args)
        safe_args = [arg if not arg.startswith('http') else '***URL***' for arg in args]
        logger.info(f"Running git command: 'git {' '.join(safe_args)}'")
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True
        )
        if check and result.returncode != 0:
            sanitized_stderr = self._sanitize_log(result.stderr)
            logger.error(f"Git command failed: {sanitized_stderr}")
            raise Exception(f"Git command failed: {sanitized_stderr}")
        return result

    @retry_api
    def _run_git_push(self, branch_name: str):
        """Push with retry logic for network resilience."""
        remote_url = f"https://github.com/{self.repo_owner}/{self.repo_name}.git"
        self._run_git_command(["push", "-u", remote_url, branch_name])

    def setup_git_config(self):
        # Ensure we have a user for committing
        self._run_git_command(["config", "user.name", "Epic-4 Bot"], check=False)
        self._run_git_command(["config", "user.email", "bot@epic4.example.com"], check=False)

    def checkout_and_push_files(self, branch_name: str, files_to_commit: List[str], message: str):
        """
        Creates or switches to a branch, adds specific files, commits, and pushes.
        This assumes we are in a checked-out git repository.
        """
        self.setup_git_config()

        # Create branch (orphan or from HEAD, usually from current state is okay for this)
        # Assuming we want to base it on the current state (config.COMMIT_SHA or HEAD)
        # But we need to make sure we don't carry over other uncommitted changes?
        # CI environment usually clean.

        # Create branch
        self._run_git_command(["checkout", "-B", branch_name])

        # Add files
        for file_path in files_to_commit:
            if os.path.exists(file_path):
                self._run_git_command(["add", file_path])
            else:
                logger.warning(f"File to commit not found: {file_path}")

        # Commit
        status = self._run_git_command(["status", "--porcelain"])
        if not status.stdout.strip():
            logger.info("No changes to commit.")
            return

        self._run_git_command(["commit", "-m", message])

        # Push with retry logic
        try:
            self._run_git_push(branch_name)
            logger.info(f"Pushed branch {branch_name}")
        except Exception as e:
            logger.error(f"Failed to push branch {branch_name}: {self._sanitize_log(str(e))}")
            raise

    @retry_api
    def find_open_pr(self, head_branch: str, base_branch: str) -> Optional[Dict]:
        url = f"{self.base_url}/pulls"
        params = {
            "head": f"{self.repo_owner}:{head_branch}",
            "base": base_branch,
            "state": "open"
        }
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        prs = resp.json()
        if prs:
            return prs[0]
        return None

    @retry_api
    def create_pr(self, head_branch: str, base_branch: str, title: str, body: str) -> Dict:
        url = f"{self.base_url}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        resp = requests.post(url, json=data, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    @retry_api
    def update_pr(self, pr_number: int, title: str, body: str) -> Dict:
        url = f"{self.base_url}/pulls/{pr_number}"
        data = {
            "title": title,
            "body": body
        }
        resp = requests.patch(url, json=data, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    @retry_api
    def add_label(self, pr_number: int, label: str):
        url = f"{self.base_url}/issues/{pr_number}/labels"
        data = {"labels": [label]}
        resp = requests.post(url, json=data, headers=self.headers)
        resp.raise_for_status()

    @retry_api
    def post_comment(self, pr_number: int, body: str):
        url = f"{self.base_url}/issues/{pr_number}/comments"
        data = {"body": body}
        resp = requests.post(url, json=data, headers=self.headers)
        resp.raise_for_status()

    def ensure_pr(self, head_branch: str, base_branch: str, title: str, body: str, labels: List[str] = []) -> str:
        pr = self.find_open_pr(head_branch, base_branch)
        if pr:
            logger.info(f"Found existing PR #{pr['number']}")
            self.update_pr(pr['number'], title, body)
            pr_number = pr['number']
        else:
            logger.info("Creating new PR")
            try:
                pr = self.create_pr(head_branch, base_branch, title, body)
                pr_number = pr['number']
            except requests.exceptions.HTTPError as e:
                if "A pull request already exists" in e.response.text:
                   # Race condition or closed PR check, try to find it again considering all states?
                   # Or just fail. But 'find_open_pr' handles open.
                   logger.error(f"Failed to create PR: {e.response.text}")
                   raise
                raise

        for label in labels:
            try:
                self.add_label(pr_number, label)
            except Exception as e:
                logger.warning(f"Failed to add label {label}: {e}")

        # Summary already included in PR body - no need for duplicate comment
        return str(pr_number)
