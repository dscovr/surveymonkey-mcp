# surveymonkey-mcp

MCP server for the [SurveyMonkey API v3](https://api.surveymonkey.com/v3/docs).

Exposes SurveyMonkey as tools usable from Claude and any MCP-compatible client.

## Features

- **Users** — get current user profile
- **Surveys** — list, get, get details, create, update, patch, delete
- **Pages** — list, get, create, update, delete
- **Questions** — list, get, create, update, delete
- **Responses** — list (metadata), list bulk (with answers), get, get details, delete, export CSV
- **Collectors** — list, get, create, update, delete
- **Collector Messages** — list, create, send
- **Collector Recipients** — list
- **Webhooks** — list, get, create, update, delete
- **Contacts** — list, get, create, delete
- **Contact Lists** — list, get, create, delete, list members

## Authentication

Obtain a **personal access token** from the [SurveyMonkey Developer Portal](https://developer.surveymonkey.com/):

1. Log in at https://developer.surveymonkey.com/
2. Go to **My Apps** → create or open an app
3. Go to **Settings** → copy your **Access Token**

The token is passed via the `SURVEYMONKEY_TOKEN` environment variable.

## Quick start

```bash
# Run directly (no install)
SURVEYMONKEY_TOKEN=your_token uvx --from git+https://github.com/dscovr/surveymonkey-mcp surveymonkey-mcp

# Or install as a uv tool
uv tool install git+https://github.com/dscovr/surveymonkey-mcp
SURVEYMONKEY_TOKEN=your_token surveymonkey-mcp
```

## Claude Desktop / MCP client configuration

Copy `.mcp.json.example` to `.mcp.json` and fill in your token:

```json
{
  "mcpServers": {
    "surveymonkey": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/dscovr/surveymonkey-mcp",
        "surveymonkey-mcp"
      ],
      "env": {
        "SURVEYMONKEY_TOKEN": "YOUR_SURVEYMONKEY_ACCESS_TOKEN"
      }
    }
  }
}
```

## Available tools (48 total)

| Tool | Description |
|---|---|
| `surveymonkey_get_me` | Get current user profile |
| `surveymonkey_list_surveys` | List surveys with filters |
| `surveymonkey_get_survey` | Get survey metadata |
| `surveymonkey_get_survey_details` | Get full survey with all pages & questions |
| `surveymonkey_create_survey` | Create a new survey |
| `surveymonkey_update_survey` | Replace a survey (PUT) |
| `surveymonkey_patch_survey` | Partially update a survey (PATCH) |
| `surveymonkey_delete_survey` | Delete a survey |
| `surveymonkey_list_pages` | List pages of a survey |
| `surveymonkey_get_page` | Get a page |
| `surveymonkey_create_page` | Create a page |
| `surveymonkey_update_page` | Update a page |
| `surveymonkey_delete_page` | Delete a page |
| `surveymonkey_list_questions` | List questions on a page |
| `surveymonkey_get_question` | Get a question |
| `surveymonkey_create_question` | Create a question |
| `surveymonkey_update_question` | Update a question |
| `surveymonkey_delete_question` | Delete a question |
| `surveymonkey_list_responses` | List responses (metadata only) |
| `surveymonkey_list_responses_bulk` | List responses with answers |
| `surveymonkey_get_response` | Get a single response |
| `surveymonkey_get_response_details` | Get a response with all answers |
| `surveymonkey_delete_response` | Delete a response |
| `surveymonkey_export_responses_csv` | Export all responses as CSV |
| `surveymonkey_list_collectors` | List collectors for a survey |
| `surveymonkey_get_collector` | Get a collector |
| `surveymonkey_create_collector` | Create a collector |
| `surveymonkey_update_collector` | Update a collector |
| `surveymonkey_delete_collector` | Delete a collector |
| `surveymonkey_list_collector_messages` | List email messages for a collector |
| `surveymonkey_create_collector_message` | Create an email message |
| `surveymonkey_send_collector_message` | Send an email message |
| `surveymonkey_list_collector_recipients` | List recipients for a collector |
| `surveymonkey_list_webhooks` | List webhooks |
| `surveymonkey_get_webhook` | Get a webhook |
| `surveymonkey_create_webhook` | Create a webhook |
| `surveymonkey_update_webhook` | Update a webhook |
| `surveymonkey_delete_webhook` | Delete a webhook |
| `surveymonkey_list_contacts` | List contacts |
| `surveymonkey_get_contact` | Get a contact |
| `surveymonkey_create_contact` | Create a contact |
| `surveymonkey_update_contact` | Update a contact |
| `surveymonkey_delete_contact` | Delete a contact |
| `surveymonkey_list_contact_lists` | List contact lists |
| `surveymonkey_get_contact_list` | Get a contact list |
| `surveymonkey_create_contact_list` | Create a contact list |
| `surveymonkey_delete_contact_list` | Delete a contact list |
| `surveymonkey_list_contact_list_members` | List members of a contact list |

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run the server locally
SURVEYMONKEY_TOKEN=your_token uv run python -m surveymonkey.server
```
