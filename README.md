# SourceSense

A GitHub metadata extraction application built using the Atlan Application SDK, Temporal and Pythin. It orchestrates a workflow that connects to the GitHub API to intelligently extract user and repository metadata, which is then processed and stored in JSON format.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Dapr CLI](https://docs.dapr.io/getting-started/install-dapr-cli/)
- [Temporal CLI](https://docs.temporal.io/cli)
- A github account with a Personal Access Token (PAT)

### Installation Guides

- [macOS Setup Guide](https://github.com/atlanhq/application-sdk/blob/main/docs/docs/setup/MAC.md)
- [Linux Setup Guide](https://github.com/atlanhq/application-sdk/blob/main/docs/docs/setup/LINUX.md)
- [Windows Setup Guide](https://github.com/atlanhq/application-sdk/blob/main/docs/docs/setup/WINDOWS.md)

## Quick Start

1. **Download required components:**

   ```bash
   uv run poe download-components
   ```

2. **Set up environment variables (see .env.example)**

3. **Start dependencies (in separate terminal):**

   ```bash
   uv run poe start-deps
   ```

4. **Run the application:**

   ```bash
   uv run main.py
   ```

    ```

5. **Send POST request through cURL**
    You can use this command to send the POST request to start the workflow.

    ```bash
    curl -X POST http://localhost:8000/workflows/v1/start -H "Content-Type:application/json" -d '{"input":"test"}'
    ```

    Upon successful completion of the workflow, you will find 3 different json files with different metadata related information of the user and their repositories.

6. **Stop the server**
    You can either chose to kill the terminals on which the processes are running or use

    ```bash
    poe stop-deps
    ```

- **Temporal UI**: <http://localhost:8233>

## Features

- **GitHub Data Retrieval**: Systematically fetches user profiles and repository information directly from the GitHub API, capturing key details like follower counts, repository stars, and project descriptions.
- **Quality Score Generation**: Analyzes the retrieved data to produce quality scores, highlighting repositories that have complete and well-documented metadata.
- **Reliable Task Execution**: Employs Temporal.io to manage the sequence of data gathering and processing, ensuring each step completes successfully.
- **Efficient and Robust Design**: Built for performance by running data collection tasks in parallel and incorporating automatic retries to handle intermittent network issues gracefully.
