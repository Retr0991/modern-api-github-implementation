
import asyncio
from datetime import timedelta
from typing import Any, Callable, Dict, List

from application_sdk.observability.decorators.observability_decorator import observability
from application_sdk.observability.logger_adaptor import get_logger
from application_sdk.observability.metrics_adaptor import get_metrics
from application_sdk.observability.traces_adaptor import get_traces
from application_sdk.workflows import WorkflowInterface
from temporalio import workflow
from temporalio.common import RetryPolicy

from app.activities import GitHubActivities
from app.types import SummaryStats, RepoMetadata, UserMetadata

logger = get_logger(__name__)
workflow.logger = logger
metrics = get_metrics()
traces = get_traces()


@workflow.defn
class GitHubWorkflow(WorkflowInterface):
    @observability(logger=logger, metrics=metrics, traces=traces)
    @workflow.run
    async def run(self, workflow_config: Dict[str, Any]):
        """
        Run the workflow.

        :param workflow_args: The workflow arguments.
        """
        activities_instance = GitHubActivities()

        workflow_args: Dict[str, Any] = workflow_config

        retry_policy = RetryPolicy(
            maximum_attempts=6,
            backoff_coefficient=2,
        )

        await workflow.execute_activity_method(
            activities_instance.preflight_check,
            workflow_args,
            retry_policy=retry_policy,
            start_to_close_timeout=self.default_start_to_close_timeout,
            heartbeat_timeout=self.default_heartbeat_timeout,
        )

        user_data, repo_data = await asyncio.gather(
            workflow.execute_activity_method(
                activities_instance.retrieve_user_profile_activity,
                workflow_args,
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=self.default_heartbeat_timeout,
            ),
            workflow.execute_activity_method(
                activities_instance.retrieve_repositories_activity,
                workflow_args,
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=self.default_heartbeat_timeout,
            ),
        )

        summary_stats: SummaryStats = await workflow.execute_activity_method(
            activities_instance.compute_summary_stats_activity,
            {"user_data": user_data, "repo_data": repo_data},
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=self.default_heartbeat_timeout,
        )

    @staticmethod
    def get_activities(activities: GitHubActivities) -> List[Callable[..., Any]]:
        """Get the list of activities for the workflow.

        Args:
            activities: The activities instance containing the workflow activities.

        Returns:
            List[Callable[..., Any]]: A list of activity methods that can be executed by the workflow.
        """
        return [
            activities.preflight_check,
            activities.retrieve_user_profile_activity,
            activities.retrieve_repositories_activity,
            activities.compute_summary_stats_activity,
        ]