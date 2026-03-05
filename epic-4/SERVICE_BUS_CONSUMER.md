# EPIC-4 Summary Generation - Service Bus Queue Consumer

## Overview
This queue consumer processes summary generation tasks from Azure Service Bus queue `code-detect-q`.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create or update `.env` file with:
```env
AZURE_SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://docpulse-queue.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=...
AZURE_SERVICE_BUS_QUEUE_NAME=epic4-summary-q
BACKEND_URL=https://backend.ashysky-0771f52f.eastasia.azurecontainerapps.io
AZURE_STORAGE_ACCOUNT_NAME=docpulse
AZURE_STORAGE_CONTAINER=ci-living-docs
```

### 3. Run the Consumer
```bash
python service_bus_consumer.py
```

## Message Format
The consumer processes summary generation messages from its dedicated queue:

```json
{
  "taskType": "generate-summary",
  "projectId": "project-123",
  "repoUrl": "https://github.com/user/repo",
  "branch": "main",
  "commitSha": "abc123",
  "githubToken": "ghp_...",
  "payload": {
    "impact_report": { ... },
    "drift_report": { ... },
    "doc_snapshot": { ... }
  }
}
```

**Note**: This service has a dedicated queue (`epic4-summary-q`), so all messages received are summary generation tasks.

## Processing Flow
1. **Receive Message**: Consumer receives task from queue
2. **Validate Input**: Check for required impact_report
3. **Update Backend**: Set status to "PROCESSING"
4. **Generate Summary**: Use SummaryGenerator to create markdown and JSON
5. **Upload to Storage**: Store summary.md and summary.json in Azure Blob
6. **Send Results**: Send summary back to backend
7. **Complete Message**: Mark message as processed

## Backend API Endpoints
- `POST /api/projects/{projectId}/stages/summary/status` - Update status
- `POST /api/projects/{projectId}/summary-results` - Send summary content

## Deployment

### Docker
```bash
docker build -t epic4-summary-consumer .
docker run --env-file .env epic4-summary-consumer python service_bus_consumer.py
```

### Azure Container Apps
Update container app environment variables and set startup command to:
```bash
python service_bus_consumer.py
```

## Monitoring
Consumer logs to stdout with INFO level. Watch for:
- "Received message: generate-summary"
- "Uploaded summary to {bucket_path}"
- "Message processed successfully: success"
- "Updated backend status for {projectId}: COMPLETED"

## Error Handling
- Invalid JSON → Dead letter with reason "InvalidJSON"
- Processing errors → Dead letter with reason "ProcessingError"
- Missing impact_report → Update backend status to "FAILED"
- Upload failures → Continue with backend update, log error

## Output Files
- `summary.md` - Human-readable markdown summary
- `summary.json` - Machine-readable JSON summary

Both files are uploaded to: `{projectId}/{commitSha}/docs/summary/`
