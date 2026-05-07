import os
import json
import base64
import requests
import zipfile
import io

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

    def get_latest_commit(self, branch="main"):
        """Get the SHA of the latest commit on the given branch."""
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
        url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/main/{file_path}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(resp.content)
            return True
        return False

    def download_full_zip(self, extract_path, progress_callback=None):
        """Download the entire repository as a zip and extract it."""
        url = f"{self.base_url}/zipball/main"
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
    def _create_blob(self, file_path):
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
        url = f"{self.base_url}/git/blobs"
        resp = requests.post(url, headers=self.headers, json={"content": content, "encoding": "base64"})
        if resp.status_code == 201:
            return resp.json()["sha"]
        return None

    def publish_changes(self, local_db_path, commit_message="Database update", progress_callback=None):
        """
        Push local changes to the GitHub repository.
        This handles creating blobs for new/modified files, building a new tree, and committing.
        """
        if not self.token:
            return False, "No token provided."

        # 1. Get latest commit SHA & Tree SHA
        latest_commit_sha = self.get_latest_commit("main")
        if not latest_commit_sha:
            return False, "Could not fetch latest commit. Repository might be empty or token invalid."

        commit_resp = requests.get(f"{self.base_url}/git/commits/{latest_commit_sha}", headers=self.headers)
        base_tree_sha = commit_resp.json()["tree"]["sha"]

        # 2. Collect all local files in categories and assets
        local_files = []
        for root, _, files in os.walk(local_db_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, local_db_path).replace("\\", "/")
                local_files.append((rel_path, abs_path))

        # 3. Create Tree structure
        tree = []
        total = len(local_files)
        for i, (rel_path, abs_path) in enumerate(local_files):
            if progress_callback:
                progress_callback(i + 1, total, f"Preparing {os.path.basename(rel_path)}")
            
            blob_sha = self._create_blob(abs_path)
            if not blob_sha:
                return False, f"Failed to process file: {rel_path}"
                
            tree.append({
                "path": rel_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha
            })

        # 4. Post New Tree
        if progress_callback:
            progress_callback(total, total, "Finalizing commit...")
            
        tree_resp = requests.post(f"{self.base_url}/git/trees", headers=self.headers, json={"base_tree": base_tree_sha, "tree": tree})
        if tree_resp.status_code != 201:
            return False, "Failed to create git tree."
        new_tree_sha = tree_resp.json()["sha"]

        # 5. Create Commit
        commit_data = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [latest_commit_sha]
        }
        new_commit_resp = requests.post(f"{self.base_url}/git/commits", headers=self.headers, json=commit_data)
        if new_commit_resp.status_code != 201:
            return False, "Failed to create commit."
        new_commit_sha = new_commit_resp.json()["sha"]

        # 6. Update branch reference
        update_ref_resp = requests.patch(
            f"{self.base_url}/git/refs/heads/main", 
            headers=self.headers, 
            json={"sha": new_commit_sha, "force": True}
        )
        if update_ref_resp.status_code != 200:
            return False, "Failed to update branch reference."

        return True, new_commit_sha
