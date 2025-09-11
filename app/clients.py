import httpx
import itertools
from typing import Any, Dict, Optional, List

from application_sdk.clients.base import BaseClient
from application_sdk.observability.logger_adaptor import get_logger
from app.types import UserMetadata, RepoMetadata

logger = get_logger(__name__)


class GitHubClient(BaseClient):
    """Thin wrapper around the GitHub REST API for metadata retrieval.

    Provides a lazily-initialized authenticated HTTP client and helpers to
    fetch normalized user details and repository lists for a given account.
    """

    def __init__(self, pat: Optional[str] = None):
        """Create a client optionally configured with a Personal Access Token.

        Args:
            pat: GitHub PAT used for authenticated requests.
        """
        super().__init__()
        self.pat = pat
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily initializes and returns a shared httpx.AsyncClient.

        The client is configured with authentication headers if a PAT is available.
        This method ensures a single client instance is used per GitHubClient instance.
        """
        if not self.client:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.pat:
                logger.info("Configuring GitHub client with Personal Access Token.")
                headers["Authorization"] = f"Bearer {self.pat}"
            else:
                logger.warning("GitHub client is not authenticated. Rate limits will be lower.")

            self.client = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers=headers,
                timeout=30.0,
            )
        return self.client

    @staticmethod
    def _normalize_user_json(user_json: Dict[str, Any]) -> UserMetadata:
        """Transforms raw GitHub user JSON into a structured UserMetadata object.

        This function handles missing data by providing sensible defaults for each field,
        ensuring a consistent data structure for downstream processing.
        """
        return {
            "name": user_json.get("name") or user_json.get("login") or "N/A",
            "node_id": user_json.get("node_id") or "N/A",
            "profile_url": user_json.get("html_url") or "N/A",
            "avatar_url": user_json.get("avatar_url") or "N/A",
            "type": user_json.get("type") or "N/A",
            "company": user_json.get("company") or "N/A",
            "location": user_json.get("location") or "N/A",
            "email": user_json.get("email") or "N/A",
            "blog": user_json.get("blog") or "N/A",
            "twitter_username": user_json.get("twitter_username") or "N/A",
            "created_at": user_json.get("created_at") or "N/A",
            "followers_url": user_json.get("followers_url") or "N/A",
            "following_url": user_json.get("following_url") or "N/A",
            "bio": user_json.get("bio") or "No bio provided.",
            "followers": user_json.get("followers", 0) or 0,
            "following": user_json.get("following", 0) or 0,
            "public_repos": user_json.get("public_repos", 0) or 0,
            "public_gists": user_json.get("public_gists", 0) or 0,
        }

    async def fetch_user_profile_data(self, username: str) -> UserMetadata:
        """Retrieves and normalizes profile data for a specified GitHub user.

        Args:
            username: The GitHub login name for the user or organization.

        Returns:
            A UserMetadata object containing the normalized profile information.
        """
        client = await self._get_client()
        user_endpoint = f"/users/{username}"
        try:
            response = await client.get(user_endpoint)
            response.raise_for_status()
            user_json = response.json()
            logger.debug("Fetched raw user data for '%s'", username)
            return self._normalize_user_json(user_json)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching user data for {username}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching user data for {username}: {e}")
            raise

    async def fetch_all_repository_data(self, username: str) -> List[RepoMetadata]:
        """Fetches all public repositories for a user, handling API pagination.

        Args:
            username: The GitHub login name to retrieve repositories for.

        Returns:
            A list of RepoMetadata objects, one for each public repository.
        """
        client = await self._get_client()
        all_repos: List[RepoMetadata] = []
        per_page = 100

        for page_num in itertools.count(1):
            repos_endpoint = f"/users/{username}/repos"
            params = {"page": page_num, "per_page": per_page}
            try:
                response = await client.get(repos_endpoint, params=params)
                response.raise_for_status()
                page_data = response.json()

                if not page_data:
                    logger.info("Finished fetching all repositories for '%s'.", username)
                    break

                normalized_page_repos = [
                    {
                        "name": repo.get("name"),
                        "description": repo.get("description"),
                        "language": repo.get("language"),
                        "star_count": repo.get("stargazers_count"),
                        "fork_count": repo.get("forks_count"),
                        "issue_count": repo.get("open_issues_count"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                        "url": repo.get("html_url"),
                    }
                    for repo in page_data
                ]
                all_repos.extend(normalized_page_repos)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on page {page_num} for {username}'s repos: {e.response.status_code}")
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred while fetching repositories for {username}: {e}")
                raise
        return all_repos