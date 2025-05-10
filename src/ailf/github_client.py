"""GitHub client module for template automation."""

import base64
import logging
import os
import time
from typing import List, Optional, Dict, Any, Union

from github import Github, GithubException, Auth
from github.Repository import Repository
from github.ContentFile import ContentFile
from github.Organization import Organization
from github.Team import Team
from github.PullRequest import PullRequest
from github.Workflow import Workflow

logger = logging.getLogger(__name__)

class GitHubClient:
    """A client for interacting with GitHub's API."""

    def __init__(
        self, 
        api_base_url: str = "https://api.github.com",
        token: Optional[str] = None,
        org_name: Optional[str] = None,
        commit_author_name: str = "Template Automation",
        commit_author_email: str = "automation@example.com",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize the GitHub client.
        
        :param api_base_url: GitHub API base URL (default: https://api.github.com)
        :param token: GitHub API token (default: read from GITHUB_TOKEN env var)
        :param org_name: Organization name for operations (optional)
        :param commit_author_name: Name for automated commits
        :param commit_author_email: Email for automated commits
        :param max_retries: Maximum number of retries for API calls
        :param retry_delay: Base delay between retries in seconds
        """
        # Get token from environment if not provided
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("No GitHub token provided. Set GITHUB_TOKEN environment variable.")
            
        # Verify token length and format
        if len(self.token) < 30:  # Personal access tokens are longer than this
            raise ValueError("GitHub token appears to be invalid (too short)")
        if not self.token.startswith(('ghp_', 'github_pat_')):
            raise ValueError("GitHub token appears to be invalid (wrong format)")

        # Initialize client with modern auth method
        self.api_base_url = api_base_url
        auth = Auth.Token(self.token)
        self.client = Github(base_url=api_base_url, auth=auth)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_pause = 5  # seconds to wait when rate limited
        
        # Set commit author info
        self.author = {
            "name": commit_author_name,
            "email": commit_author_email
        }
        
        # Test authentication
        try:
            self.client.get_user().login
        except GithubException as e:
            if e.status == 401:
                raise ValueError("GitHub token is invalid or expired") from e
            raise
        
        # Get organization if specified
        self.org = None
        if org_name:
            try:
                self.org = self._retry_api_call(
                    lambda: self.client.get_organization(org_name),
                    retries=1,  # Don't retry org lookup
                    error_msg=f"Failed to get organization {org_name}"
                )
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"Organization {org_name} not found")
                else:
                    raise

    def _retry_api_call(self, func, retries=None, error_msg="API call failed"):
        """Retry an API call with exponential backoff.
        
        :param func: Function to retry
        :param retries: Number of retries (default: self.max_retries)
        :param error_msg: Error message prefix for logging
        :return: Result of the API call
        :raises GithubException: If all retries fail
        """
        retries = retries if retries is not None else self.max_retries
        last_error = None
        
        for attempt in range(retries):
            try:
                return func()
            except GithubException as e:
                last_error = e
                if e.status == 404:  # Don't retry not found errors
                    raise
                if e.status == 401:  # Don't retry auth errors
                    raise
                if attempt < retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{retries}): {str(e)}")
                    time.sleep(delay)
                    
        raise last_error

    def create_repository_from_template(
        self,
        template_repo_name: str,
        new_repo_name: str,
        private: bool = True,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> Repository:
        """Create a new repository from a template.
        
        Args:
            template_repo_name: Name of the template repository
            new_repo_name: Name for the new repository
            private: Whether the new repository should be private
            description: Description for the new repository
            topics: List of topics to add to the repository
            
        Returns:
            The newly created repository
            
        Raises:
            GithubException: If template doesn't exist or repo creation fails
        """
        template_repo = self.org.get_repo(template_repo_name)
        
        # Create repository from template
        new_repo = self.org.create_repository_from_template(
            name=new_repo_name,
            template_repository=template_repo,
            private=private,
            description=description or f"Repository created from template: {template_repo_name}"
        )
        
        # Add topics if provided
        if topics:
            new_repo.replace_topics(topics)
            
        logger.info(f"Created new repository: {new_repo_name} from template: {template_repo_name}")
        return new_repo

    def set_team_access(self, repo: Repository, team_slug: str, permission: str = "admin") -> None:
        """Give a team access to a repository.
        
        Args:
            repo: The repository to grant access to
            team_slug: The team's slug identifier
            permission: The permission level to grant (pull, push, admin)
            
        Raises:
            GithubException: If team doesn't exist or permission grant fails
        """
        try:
            team = self.org.get_team_by_slug(team_slug)
            team.add_to_repos(repo)
            team.set_repo_permission(repo, permission)
            logger.info(f"Granted {permission} access to team {team_slug} for repo {repo.name}")
        except GithubException as e:
            logger.error(f"Failed to set team access: {e}")
            raise

    def write_file(
        self,
        repo: Repository,
        path: str,
        content: str,
        branch: str = "main",
        commit_message: Optional[str] = None
    ) -> ContentFile:
        """Write or update a file in a repository.
        
        Args:
            repo: The repository to write to
            path: Path where to create/update the file
            content: Content to write to the file
            branch: Branch to commit to
            commit_message: Commit message to use
            
        Returns:
            The created/updated file content
            
        Raises:
            GithubException: If file operation fails
        """
        try:
            # Convert content to base64
            content_bytes = content.encode("utf-8")
            content_base64 = base64.b64encode(content_bytes).decode("utf-8")
            
            # Try to get existing file
            try:
                file = repo.get_contents(path, ref=branch)
                # Update existing file
                result = repo.update_file(
                    path=path,
                    message=commit_message or f"Update {path}",
                    content=content_base64,
                    sha=file.sha,
                    branch=branch,
                    committer={
                        "name": self.commit_author_name,
                        "email": self.commit_author_email
                    }
                )
                logger.info(f"Updated file {path} in repo {repo.name}")
                return result["content"]
            except GithubException as e:
                if e.status != 404:  # Only handle "not found" errors
                    raise
                
                # Create new file
                result = repo.create_file(
                    path=path,
                    message=commit_message or f"Create {path}",
                    content=content_base64,
                    branch=branch,
                    committer={
                        "name": self.commit_author_name,
                        "email": self.commit_author_email
                    }
                )
                logger.info(f"Created new file {path} in repo {repo.name}")
                return result["content"]
                
        except GithubException as e:
            logger.error(f"Failed to write file {path}: {e}")
            raise

    def read_file(
        self,
        repo: Repository,
        path: str,
        ref: str = "main"
    ) -> str:
        """Read a file from a repository.
        
        Args:
            repo: The repository to read from
            path: Path to the file to read
            ref: Git reference (branch, tag, commit) to read from
            
        Returns:
            The file contents as a string
            
        Raises:
            GithubException: If file doesn't exist or read fails
        """
        try:
            file = repo.get_contents(path, ref=ref)
            content = base64.b64decode(file.content).decode("utf-8")
            return content
        except GithubException as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise

    def get_repository(
        self,
        repo_name: str,
        create: bool = False,
        owning_team: Optional[str] = None
    ) -> Repository:
        """Get or create a GitHub repository.
        
        Args:
            repo_name: Full repository name (owner/repo) or just repo name if using org
            create: Whether to create the repo if it doesn't exist
            owning_team: Name of team to grant access if repo is created
            
        Returns:
            Repository: The GitHub repository object
            
        Raises:
            GithubException: If repository doesn't exist and create=False
            
        Example:
            ```python
            repo = client.get_repository(
                "my-service",
                create=True,
                owning_team="developers"
            )
            ```
        """
        try:
            # If org is set and repo_name doesn't have a /, try org first
            if self.org and '/' not in repo_name:
                try:
                    return self.org.get_repo(repo_name)
                except GithubException as e:
                    if e.status != 404:
                        raise
                    if create:
                        repo = self.org.create_repo(repo_name, auto_init=True)
                        if owning_team:
                            team = self.org.get_team_by_slug(owning_team)
                            team.set_repo_permission(repo, "admin")
                        return repo
                    raise
            
            # Try as full repo name (owner/repo)
            try:
                return self.client.get_repo(repo_name)
            except GithubException as e:
                if e.status != 404:
                    raise
                if not create:
                    raise
                
                # Create in user account if no org
                user = self.client.get_user()
                if '/' in repo_name:
                    repo_name = repo_name.split('/')[-1]
                return user.create_repo(repo_name, auto_init=True)
                
        except Exception as e:
            logger.error(f"Error accessing repository {repo_name}: {str(e)}")
            raise

    def update_repository_topics(self, repo_name: str, topics: List[str]) -> None:
        """Update the topics of a repository.
        
        Args:
            repo_name: Name of the repository
            topics: List of topics to set
            
        Raises:
            GithubException: If the operation fails
        """
        try:
            repo = self.get_repository(repo_name)
            repo.replace_topics(topics)
        except Exception as e:
            logger.error(f"Error updating topics for {repo_name}: {str(e)}")
            raise
