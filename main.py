import asyncio
import os
import sys
from dotenv import load_dotenv

from app.activities import GitHubActivities
from app.workflow import GitHubWorkflow
from application_sdk.application import BaseApplication
from application_sdk.observability.logger_adaptor import get_logger

APP_NAME = "github_connector"
REQUIRED_ENV_VARS = ["GITHUB_USERNAME", "GITHUB_PAT"]

logger = get_logger(__name__)

def _configure_and_validate_environment():
    """
    Load environment variables from .env file and ensure critical variables are set.
    Exits the application if required configuration is missing.
    """
    load_dotenv()
    missing_vars = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing_vars:
        logger.critical(
            "Fatal: Missing required environment variables: %s. Please check your .env file.",
            ", ".join(missing_vars),
        )
        sys.exit(1)
    logger.info("Environment configuration loaded and validated successfully.")


async def launch_app():
    """
    Initializes and launches the application, setting up the Temporal worker and the web server.
    """
    _configure_and_validate_environment()

    logger.info("Initializing the %s application.", APP_NAME)
    app_instance = BaseApplication(name=APP_NAME)

    await app_instance.setup_workflow(
        workflow_and_activities_classes=[(GitHubWorkflow, GitHubActivities)],
        passthrough_modules=[
            "requests",
            "httpx",
            "urllib3",
            "warnings",
            "os",
            "grpc",
            "pyatlan",
        ],
    )

    await app_instance.start_worker()

    await app_instance.setup_server(workflow_class=GitHubWorkflow)
    await app_instance.start_server()


if __name__ == "__main__":
    asyncio.run(launch_app())
