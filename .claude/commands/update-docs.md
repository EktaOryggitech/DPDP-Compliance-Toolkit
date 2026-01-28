# Update Documentation After Code Check-in

When code is checked into the GitHub repository, update the Obsidian documentation vault to reflect the changes.

## Obsidian Vault Location

**Local Path**: `C:\Oryggitech_Projects_April_2024_Onwards\Obsidian\DPDP-Compliance-Toolkit`

## Obsidian API Connection

- **Endpoint**: `https://127.0.0.1:27124/`
- **API Key**: `1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c`
- **Use `-k` flag** for curl to skip certificate verification

## Instructions

### Step 1: Get Latest Commit Information

```bash
git log -1 --format="%H %s"
git diff --stat HEAD~1
```

### Step 2: Identify Changed Areas

Analyze the changed files and categorize:
- **Backend changes** (detectors, API, models, workers)
- **Frontend changes** (components, pages, stores, hooks)
- **Configuration changes** (Docker, env, config)
- **Schema changes** (database models)

### Step 3: Update Documentation Files

Update the following files in the Obsidian vault based on changes:

| Changed Area | Documentation File to Update |
|--------------|------------------------------|
| Detectors (`backend/app/detectors/`) | `2-Code-Flows/04-DPDP-Detection-Flow.md` |
| Auth (`backend/app/api/v1/auth.py`) | `2-Code-Flows/07-Authentication-Flow.md` |
| Scanners (`backend/app/scanners/`) | `2-Code-Flows/02-Web-Scanning-Flow.md` or `03-Windows-Scanning-Flow.md` |
| Reports (`backend/app/reports/`) | `2-Code-Flows/05-Report-Generation-Flow.md` |
| WebSocket (`backend/app/api/v1/ws.py`) | `2-Code-Flows/06-WebSocket-Progress-Flow.md` |
| API Routes (`backend/app/api/`) | `3-API-Reference/01-API-Overview.md` |
| Models (`backend/app/models/`) | `4-Models/01-Database-Schema.md` |
| Docker (`docker/`) | `5-Deployment/01-Docker-Setup.md` |
| Architecture changes | `1-Architecture/01-System-Overview.md` |
| Tech stack changes | `1-Architecture/02-Tech-Stack.md` |
| Main application flow | `2-Code-Flows/01-Main-Application-Flow.md` |

### Step 4: Always Update Index

Always update `0-Index.md` with:
- New sync date and commit hash
- Summary of changes in "Recent Updates" section
- Any new features added to "Key Features" list

### Step 5: Use Obsidian API or Direct File Edit

**Read a file via API:**
```bash
curl -s -k "https://127.0.0.1:27124/vault/{path}" -H "Authorization: Bearer 1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c"
```

**Update a file via API:**
```bash
curl -s -k -X PUT "https://127.0.0.1:27124/vault/{path}" \
  -H "Authorization: Bearer 1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c" \
  -H "Content-Type: text/markdown" \
  -d "content here"
```

**Alternative: Direct file edit** (if Obsidian API is unavailable):
Edit files directly at `C:\Oryggitech_Projects_April_2024_Onwards\Obsidian\DPDP-Compliance-Toolkit\`

## Documentation Standards

### Mermaid Diagrams
Use Mermaid for flow diagrams in documentation.

### Code References
Include file paths and line numbers when referencing code.

### Tags
Add relevant tags at the end of each document:
`#DPDP #Authentication #Security #Detection`

## Sync Checklist

- [ ] Update `0-Index.md` sync date and commit hash
- [ ] Add changes to "Recent Updates" section
- [ ] Update affected flow documents
- [ ] Update API reference if endpoints changed
- [ ] Update database schema if models changed
- [ ] Add new features to Key Features list if applicable
