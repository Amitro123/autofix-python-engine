# AutoFix Setup Guide

## For End Users (MVP Distribution)

**No setup required!** The AutoFix CLI works out of the box with no configuration needed.

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the CLI
python autofix_cli_interactive.py your_script.py
```

### Metrics Collection

The CLI **automatically and transparently** collects anonymous usage metrics to help improve the tool. This includes:

- Error types encountered and fix success rates
- Performance data (fix duration, script execution time)
- No personal information or code content is collected

**Important**: 
- ✅ No Firebase credentials needed from users
- ✅ No environment setup required
- ✅ Metrics are sent securely to the developer's Firebase project
- ✅ Only the developer can access collected data
- ✅ Collection happens transparently in the background

### What Metrics Are Collected

The CLI collects the following anonymous data to improve the tool:

```json
{
  "app_id": "autofix-default-app",
  "script_path": "Filename only (no full paths or personal info)", 
  "status": "Operation result (success, failure, fix_succeeded, etc.)",
  "original_error": "Error type (TypeError, IndexError, etc.)",
  "error_details": {
    "error_type": "Specific error category",
    "line_number": "Line where error occurred",
    "fix_applied": "Whether a fix was attempted",
    "operation": "Type of operation performed"
  },
  "message": "Human-readable status description",
  "timestamp": "When the event occurred (UTC)",
  "fix_attempts": "Number of fix attempts made",
  "fix_duration": "Time spent on fixing (seconds)"
}
```

**Privacy**: No code content, file contents, or personal information is collected.

---

## For Developers Only

### Production Metrics Setup

The CLI uses **Firebase Admin SDK** with a service account key for production metrics collection:

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create new project and enable Firestore

2. **Generate Service Account Key**:
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Save as `firebase-key.json` in the project root

3. **Install Firebase Admin SDK**:
   ```bash
   pip install firebase-admin
   ```

**Distribution Security**:
- ✅ `firebase-key.json` is in `.gitignore` (never committed)
- ✅ Users receive CLI without credentials
- ✅ Metrics collection is transparent to users
- ✅ Only developer can access collected data

### Alternative: REST API Testing

For testing without Admin SDK, you can use the REST API approach:

1. **Get Web API Key**: Project Settings > General > Web API Key
2. **Set Environment Variables**:
   ```bash
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_WEB_API_KEY=your-web-api-key
   ```
3. **Use REST API client**: Import from `firestore_client.py`

**Note**: The main CLI uses Admin SDK for production. REST API is for testing only.

### Security Architecture

| Aspect | Description |
|--------|-------------|
| **User Experience** | Zero configuration required |
| **Credentials** | Service account key (developer only, not distributed) |
| **Data Access** | Only developer can access collected metrics |
| **Privacy** | No personal info or code content collected |
| **Distribution** | Safe - credentials excluded from distribution |

### How It Works

- ✅ Developer has `firebase-key.json` for metrics collection
- ✅ Users receive CLI without any credentials
- ✅ Metrics collection happens transparently
- ✅ Graceful fallback when credentials missing
- ✅ No user setup required

The CLI is **production-ready** with secure, transparent metrics collection using Firebase Admin SDK.
