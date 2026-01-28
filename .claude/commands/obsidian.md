# Obsidian Local REST API Connection

Connect to the Obsidian vault using the Local REST API plugin.

## Connection Details

- **HTTPS Endpoint**: `https://127.0.0.1:27124/`
- **HTTP Endpoint**: `http://127.0.0.1:27123/` (if enabled)
- **API Key**: `1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c`

## How to Connect

Use curl with the `-k` flag to skip certificate verification for HTTPS:

```bash
curl -s -k https://127.0.0.1:27124/vault/ -H "Authorization: Bearer 1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c"
```

## Common API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status and info |
| `/vault/` | GET | List all files in vault |
| `/vault/{path}` | GET | Read a specific note |
| `/vault/{path}` | PUT | Create/update a note |
| `/vault/{path}` | DELETE | Delete a note |
| `/search/simple/?query={query}` | GET | Search notes |

## Example Commands

**List vault contents:**
```bash
curl -s -k https://127.0.0.1:27124/vault/ -H "Authorization: Bearer 1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c"
```

**Read a note:**
```bash
curl -s -k "https://127.0.0.1:27124/vault/Welcome.md" -H "Authorization: Bearer 1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c"
```

**Create/update a note:**
```bash
curl -s -k -X PUT "https://127.0.0.1:27124/vault/MyNote.md" -H "Authorization: Bearer 1f9c452534ebe3b569b324148ba6d37a4970d142de64c05950beaf0a603d9a1c" -H "Content-Type: text/markdown" -d "# My Note Content"
```

## Documentation

Full API documentation: https://coddingtonbear.github.io/obsidian-local-rest-api/
