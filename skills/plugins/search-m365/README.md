# search-m365

Cross-entity Microsoft 365 search — find emails, files, events, chat messages, and SharePoint content in one query.

## Installation

```
/plugin install search-m365@akarelin-skills
```

Requires: `work-m365` plugin (shares its `m365.py` script), `pip install msal requests`

## Searchable types

| Type | Content |
|------|---------|
| message | Outlook emails |
| driveItem | OneDrive / SharePoint files |
| event | Calendar events |
| chatMessage | Teams chat messages |
| site | SharePoint sites |
| list / listItem | SharePoint lists |

## Usage

Ask Claude to "search my emails for X", "find file in OneDrive", or "search across M365 for Y".
