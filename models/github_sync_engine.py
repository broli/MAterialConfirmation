import os
import json
import base64
import requests
import zipfile
import io
import subprocess
from models.config_manager import ConfigManager

class GithubSyncEngine:
    def __init__(self, owner, repo, token=None):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_latest_commit(self, branch=None):
        """Get the SHA of the latest commit on the given branch."""
        if branch is None:
            branch = ConfigManager.get("github_branch") or "main"
        url = f"{self.base_url}/commits/{branch}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json()["sha"]
        return None

    def get_changed_files(self, base_sha, head_sha):
        """Compare two commits and return a list of changed files."""
        url = f"{self.base_url}/compare/{base_sha}...{head_sha}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("files", [])
        return None

    def download_file(self, file_path, target_path):
        """Download a single raw file from the repository."""
        branch = ConfigManager.get("github_branch") or "main"
        url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{branch}/{file_path}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(resp.content)
            return True
        return False

    def download_full_zip(self, extract_path, progress_callback=None):
        """Download the entire repository as a zip and extract it."""
        branch = ConfigManager.get("github_branch") or "main"
        url = f"{self.base_url}/zipball/{branch}"
        resp = requests.get(url, headers=self.headers, stream=True)
        if resp.status_code == 200:
            total_size = int(resp.headers.get('content-length', 0))
            block_size = 1024 * 8
            data = bytearray()
            for chunk in resp.iter_content(block_size):
                if chunk:
                    data.extend(chunk)
                    if progress_callback and total_size:
                        progress_callback(len(data), total_size)
            
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                # The root folder in zipball is owner-repo-sha. We want to extract its contents.
                root_dir = z.namelist()[0].split('/')[0] + '/'
                
                if progress_callback:
                    progress_callback(-1, -1) # Signaling extraction phase
                
                for member in z.namelist():
                    if member.startswith(root_dir) and not member.endswith('/'):
                        rel_path = member[len(root_dir):]
                        target = os.path.join(extract_path, rel_path)
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with open(target, "wb") as f:
                            f.write(z.read(member))
            return True
        return False

    # --- PUBLISH / PUSH LOGIC (Admin Only) ---
    def publish_changes(self, local_db_path, commit_message="Database update", progress_callback=None):
        """
        Push local changes to the GitHub repository using native git commands.
        """
        if not self.token:
            return False, "No token provided."

        branch = ConfigManager.get("github_branch") or "main"
        
        # 1. Check if git is installed
        try:
            subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            return False, "Git is not installed. Administrators must install Git to publish the database."

        # 2. Initialize git if necessary
        git_dir = os.path.join(local_db_path, ".git")
        if not os.path.exists(git_dir):
            if progress_callback: progress_callback(0, 0, "Initializing git repository locally...")
            subprocess.run(["git", "init"], cwd=local_db_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Ensure we start on the correct default branch
            subprocess.run(["git", "checkout", "-b", branch], cwd=local_db_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Create a basic .gitignore if it doesn't exist
            gitignore_path = os.path.join(local_db_path, ".gitignore")
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w") as f:
                    f.write(".*\\n!*.gitignore\\nbackup*/\\n*backup*/\\nsessions/\\nlogs/\\noutput/\\nversion.txt\\n")

        # 3. Setup remote with token
        remote_url = f"https://{self.token}@github.com/{self.owner}/{self.repo}.git"
        
        try:
            # Check existing remote
            remotes = subprocess.run(["git", "remote"], cwd=local_db_path, check=True, stdout=subprocess.PIPE, text=True).stdout
            if "origin" in remotes:
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=local_db_path, check=True, stdout=subprocess.PIPE)
            else:
                subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=local_db_path, check=True, stdout=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            return False, f"Failed to configure git remote: {e.stderr if hasattr(e, 'stderr') else str(e)}"

        # 4. Configure user to avoid commit errors
        subprocess.run(["git", "config", "user.name", "PKB Admin"], cwd=local_db_path)
        subprocess.run(["git", "config", "user.email", "admin@pkb.local"], cwd=local_db_path)

        # 5. Fetch to test connection and permissions (intercepts 403 early)
        if progress_callback: progress_callback(0, 0, "Connecting to GitHub...")
        fetch_res = subprocess.run(["git", "fetch", "origin"], cwd=local_db_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if fetch_res.returncode != 0:
            err_msg = fetch_res.stderr.decode('utf-8') if fetch_res.stderr else ""
            if "403" in err_msg:
                return False, "Failed to connect to GitHub (403 Forbidden). Your token does NOT have write access. Please generate a new GitHub Personal Access Token with the 'repo' scope."
            elif "not found" in err_msg.lower():
                return False, f"Repository '{self.owner}/{self.repo}' not found on GitHub. Please create it first."

        # 6. Stage changes
        if progress_callback: progress_callback(0, 0, "Staging files...")
        try:
            subprocess.run(["git", "add", "."], cwd=local_db_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            return False, f"Failed to stage files: {e.stderr.decode('utf-8') if e.stderr else 'Unknown error'}"

        # 7. Commit changes
        if progress_callback: progress_callback(0, 0, "Committing changes...")
        try:
            # Check if there are changes to commit
            status = subprocess.run(["git", "status", "--porcelain"], cwd=local_db_path, stdout=subprocess.PIPE, text=True).stdout
            if status.strip():
                subprocess.run(["git", "commit", "-m", commit_message], cwd=local_db_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            return False, f"Failed to commit: {e.stderr.decode('utf-8') if e.stderr else 'Unknown error'}"

        # 8. Push changes
        if progress_callback: progress_callback(0, 0, f"Pushing to {branch}...")
        try:
            # Ensure local branch matches the target branch name
            subprocess.run(["git", "branch", "-M", branch], cwd=local_db_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Try a regular push first, then force if it fails (e.g., first push or overwritten history)
            push_res = subprocess.run(["git", "push", "-u", "origin", branch], cwd=local_db_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if push_res.returncode != 0:
                err_msg = push_res.stderr.decode('utf-8') if push_res.stderr else ""
                if "403" in err_msg:
                    return False, "Push failed (403 Forbidden). Your token does NOT have write access. Ensure it has the 'repo' scope."
                
                # If push fails, try force push (common for new repos or forceful syncs in this specific app design)
                force_push_res = subprocess.run(["git", "push", "-u", "origin", branch, "--force"], cwd=local_db_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if force_push_res.returncode != 0:
                    err_msg_force = force_push_res.stderr.decode('utf-8') if force_push_res.stderr else ""
                    if "403" in err_msg_force:
                        return False, "Force push failed (403 Forbidden). Your token does NOT have write access. Ensure it has the 'repo' scope."
                    return False, f"Failed to push to GitHub: {err_msg_force}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to push to GitHub: {e.stderr.decode('utf-8') if e.stderr else 'Check your token and repository name.'}"

        # Ensure latest_commit_sha is returned for compatibility
        try:
            latest_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=local_db_path, stdout=subprocess.PIPE, text=True, check=True).stdout.strip()
        except Exception:
            latest_sha = "unknown_sha"
            
        return True, latest_sha
