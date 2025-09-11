
from typing import Any, Dict, List, Optional
from application_sdk.activities import ActivitiesInterface
from application_sdk.activities.common.models import ActivityStatistics
from application_sdk.activities.common.utils import auto_heartbeater
from application_sdk.observability.decorators.observability_decorator import observability
from application_sdk.observability.logger_adaptor import get_logger
from application_sdk.observability.metrics_adaptor import get_metrics
from application_sdk.observability.traces_adaptor import get_traces
from temporalio import activity
from app.clients import GitHubClient
from app.types import SummaryStats, RawData, RepoMetadata, UserMetadata
import json
import os

logger = get_logger(__name__)
activity.logger = logger
metrics = get_metrics()
traces = get_traces()

def _resolve_credentials(workflow_args: Optional[Dict[str, Any]] = None) -> tuple[Optional[str], Optional[str]]:
    """Resolve username and PAT preferring workflow args, then environment.

    Evaluated at call time to support test-time environment overrides.
    """
    username = (workflow_args or {}).get("username") if workflow_args else None
    pat = (workflow_args or {}).get("pat") if workflow_args else None
    if not username:
        username = os.getenv("GITHUB_USERNAME")
    if not pat:
        pat = os.getenv("GITHUB_PAT")
    return username, pat
 


class GitHubActivities(ActivitiesInterface):
    """Collection of async tasks used by the workflow to gather and enrich GitHub data."""

    @observability(logger=logger, metrics=metrics, traces=traces)
    @activity.defn
    @auto_heartbeater
    async def preflight_check(self, workflow_args: Dict[str, Any]) -> Optional[ActivityStatistics]:
        """Quick sanity check that a GitHub token exists and works.

        Makes a minimal API request with the configured PAT to ensure credentials
        are present and usable before running heavier activities.
        """
        try:
            # Prefer explicit workflow args when provided, fall back to environment at runtime
            effective_username, effective_pat = _resolve_credentials(workflow_args)

            if not effective_pat:
                raise ValueError("Personal Access Token (PAT) is missing.")
            if not effective_username:
                raise ValueError("GitHub username is missing.")

            client = GitHubClient(pat=effective_pat)
            await client.fetch_user_profile_data(username=effective_username)
            logger.info("Preflight check passed successfully.")
            return None
        except Exception as e:
            logger.error(f"Preflight check failed: {e}")
            raise
        # TODO: Consider explicit validation of the 'username' input as a separate guard.

    @observability(logger=logger, metrics=metrics, traces=traces)
    @activity.defn
    @auto_heartbeater
    async def retrieve_user_profile_activity(self, workflow_args: Dict[str, Any]) -> UserMetadata:
        """Retrieve profile details for a GitHub account and persist them to disk.

        Args:
            workflow_args: Workflow configuration inputs (e.g., username/PAT in env).

        Returns:
            UserMetadata: Normalized user or org profile fields.
        """
    # Prefer workflow args over environment variables when provided
        effective_username, effective_pat = _resolve_credentials(workflow_args)

        client = GitHubClient(pat=effective_pat)
        user_metadata = await client.fetch_user_profile_data(username=effective_username)  # type: ignore[arg-type]
        output_file = "github_user_profile.json"
        with open(output_file, "w") as f:
            json.dump(user_metadata, f, indent=4)
        
        logger.info("Wrote user metadata for '%s' to '%s'", effective_username, output_file)
        return user_metadata

    @observability(logger=logger, metrics=metrics, traces=traces)
    @activity.defn
    @auto_heartbeater
    async def retrieve_repositories_activity(self, workflow_args: Dict[str, Any]) -> List[RepoMetadata]:
        """List public repositories for an account and store structured details.

        Args:
            workflow_args: Workflow inputs used by the activity (env for auth/user).

        Returns:
            List[RepoMetadata]: Per-repo information such as stars, language, and URLs.
        """
        effective_username, effective_pat = _resolve_credentials(workflow_args)

        client = GitHubClient(pat=effective_pat)
        repository_metadata = await client.fetch_all_repository_data(username=effective_username)  # type: ignore[arg-type]
        output_file = "github_repositories.json"
        with open(output_file, "w") as f:
            json.dump(repository_metadata, f, indent=4)
        
        logger.info("Wrote %d repositories for '%s' to '%s'", len(repository_metadata), effective_username, output_file)
        return repository_metadata
    
    @observability(logger=logger, metrics=metrics, traces=traces)
    @activity.defn
    @auto_heartbeater
    async def extract_keywords_activity(self, repo_metadata: List[RepoMetadata]) -> List[RepoMetadata]:
        """Deprecated: tagging removed. Returns input unchanged for backward-compatibility."""
        return repo_metadata
    
    @observability(logger=logger, metrics=metrics, traces=traces)
    @activity.defn
    @auto_heartbeater
    async def compute_summary_stats_activity(self, raw_data: RawData) -> SummaryStats:
        """Compute concise summary statistics from user and repo data.

        Args:
            raw_data: Bundle containing 'user_data' and 'repo_data' previously fetched.

        Returns:
            SummaryStats: Aggregated counts derived from inputs.
        """
        logger.debug("raw_data type in metrics activity: %s", type(raw_data))
        user_metadata = raw_data.get("user_data", {})
        repo_metadata = raw_data.get("repo_data", [])

        repo_count = len(repo_metadata)
        followers = user_metadata.get("followers", 0) or 0
        following = user_metadata.get("following", 0) or 0
        public_gists = user_metadata.get("public_gists", 0) or 0

        summary_stats: SummaryStats = {
            "total_public_repos": repo_count,
            "total_followers": followers,
            "total_following": following,
            "total_public_gists": public_gists,
        }

        output_file = "github_summary_stats.json"
        with open(output_file, "w") as f:
            json.dump(summary_stats, f, indent=4)

        logger.info("Computed summary stats; results written to '%s'.", output_file)
        return summary_stats