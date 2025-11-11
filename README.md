# Databricksters Hook Generator

A Databricks app that transforms technical blog content into high-performing titles and subtitles. Built for senior data engineers, platform engineers, and data/ML architects.

## What it does

Turn any technical blog draft, outline, or final article into:
- **5 click-magnet titles** (55-75 characters, following proven patterns)
- **5 promise-driven subtitles** (value + clarity + credibility)
- **YouTube thumbnail concepts** (2 distinct thumbnail text concepts with detailed image descriptions)

Each title pairs logically with its corresponding subtitle, covering different angles: cost/efficiency, performance/latency, and reliability/operability/governance.

### Features
- **Content Hook Generation**: Generate high-performing titles and subtitles tailored to technical content
- **Thumbnail Concept Generation**: Generate thumbnail text and detailed image descriptions
- **Copy to Clipboard**: Easily copy generated content for immediate use
- **Non-blocking UI**: Asynchronous generation prevents UI freezing during longer operations

### ⚠️ Known Issues
- **Image Generation Not Working**: While the app generates thumbnail concepts (text + descriptions), the actual image generation via `databricks-shutterstock-imageai` endpoint is currently not functioning. Users will receive thumbnail concepts that can be used as prompts for external image generation tools (DALL-E, Midjourney, Stable Diffusion, etc.)

## Local Development Setup

### Prerequisites
- Python 3.9+ installed
- Databricks CLI installed and configured
- Profile `e2-demo-field-eng` configured in `~/.databrickscfg`

### Initial Setup

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Set the serving endpoint environment variable:**
   ```bash
   export SERVING_ENDPOINT=databricks-gemini-2-5-pro
   ```
   
   Note: You can use any chat-compatible Databricks endpoint. Use the name of your configured serving endpoint.

3. **Run the app locally:**
   ```bash
   python app.py
   ```
   
   The app will be available at http://127.0.0.1:8050/

4. **Use the Hook Generator:**
   - Paste your blog content (draft, outline, or final article) into the text area
   - Click "✨ Generate Hooks" to create titles and subtitles
   - Click "🎨 Generate Thumbnails" to create YouTube thumbnail concepts and AI-generated images
   - Use "📋 Copy All" / "📋 Copy Concepts" to copy the generated content to your clipboard
   - Click "🗑️ Clear" to reset and start with new content

### Syncing Changes with Databricks Workspace

To sync your local changes back to the Databricks workspace (bidirectional sync):

```bash
databricks sync --watch --profile e2-demo-field-eng . /Workspace/Users/jitesh.soni@databricks.com/databricks_apps/databricksters-hook-generator_2025_11_11-03_06/dash-chatbot-app
```

This command will:
- Watch for file changes in the current directory
- Automatically sync changes to the Databricks workspace
- Enable bidirectional synchronization

## Deploying to Databricks Apps

### Prerequisites for Deployment
1. **Databricks CLI** installed and configured
2. **Databricks workspace** with Apps enabled
3. **Service Principal or User Profile** configured in `~/.databrickscfg`
4. Access to a **Databricks serving endpoint** (e.g., `databricks-gemini-2-5-pro`)

### Step-by-Step Deployment Guide

#### Step 1: Prepare Your Files

**IMPORTANT**: Do NOT upload the `venv` directory. Only upload app files.

Create a clean deployment directory:
```bash
mkdir -p /tmp/hook-generator-deploy
cp app.py app.yaml HookGenerator.py model_serving_utils.py requirements.txt DatabricksChatbot.py /tmp/hook-generator-deploy/
```

#### Step 2: Upload to Databricks Workspace

Replace `YOUR_USERNAME` with your Databricks username:

```bash
# Set your workspace path
WORKSPACE_PATH="/Workspace/Users/YOUR_USERNAME@databricks.com/apps/hook-generator"

# Create the directory
databricks workspace mkdirs --profile YOUR_PROFILE $WORKSPACE_PATH

# Upload files
databricks workspace import-dir /tmp/hook-generator-deploy $WORKSPACE_PATH
```

#### Step 3: Deploy the App

```bash
databricks apps deploy hook-generator \
  --profile YOUR_PROFILE \
  --source-code-path $WORKSPACE_PATH
```

Example with actual values:
```bash
databricks apps deploy databricksters-hook-generator \
  --profile e2-demo-field-eng \
  --source-code-path /Workspace/Users/jitesh.soni@databricks.com/databricks_apps/databricksters-hook-generator_2025_11_11-03_06/dash-chatbot-app
```

#### Step 4: Check Deployment Status

```bash
databricks apps get hook-generator --profile YOUR_PROFILE -o json
```

Look for:
- `"state": "RUNNING"` - App is running successfully
- `"url": "https://..."` - Your app's public URL

### Subsequent Deployments

After the initial deployment, you can redeploy with just:

```bash
databricks apps deploy hook-generator --profile YOUR_PROFILE
```

### Troubleshooting Deployment

**Issue**: "File is larger than the maximum allowed file size"
- **Solution**: Make sure you're NOT uploading the `venv` directory. Use the clean deployment approach above.

**Issue**: "Failed to reach SUCCEEDED, got FAILED"
- **Solution**: Check the app logs:
  ```bash
  databricks apps logs hook-generator --profile YOUR_PROFILE
  ```

**Issue**: "Missing package or wrong package version"
- **Solution**: Ensure all dependencies are listed in `requirements.txt`

**Issue**: "Missing environment variable"
- **Solution**: Add environment variables to `app.yaml`:
  ```yaml
  env:
    - name: SERVING_ENDPOINT
      value: databricks-gemini-2-5-pro
  ```

### Accessing Your Deployed App

Once deployed, get your app URL:
```bash
databricks apps get hook-generator --profile YOUR_PROFILE -o json | grep '"url"'
```

The URL will look like: `https://hook-generator-XXXXXXXX.aws.databricksapps.com`

## Project Structure

- `app.py` - Main application entry point
- `app.yaml` - Databricks app configuration
- `HookGenerator.py` - Hook generator UI component (handles hooks and thumbnails)
- `model_serving_utils.py` - Utilities for model serving endpoint integration (includes hook and thumbnail generation logic with image generation)
- `requirements.txt` - Python dependencies
- `DatabricksChatbot.py` - Original chatbot component (kept for reference)
- `TEST_RESULTS.md` - Test results and validation documentation

## Environment Variables

- `SERVING_ENDPOINT` - Name of the Databricks serving endpoint to use for text generation (required)
  - Recommended: `databricks-gemini-2-5-pro`
  - Must be a chat-compatible endpoint

## Technical Details

### Endpoints Used
- **Text Generation**: Uses the configured `SERVING_ENDPOINT` (e.g., `databricks-gemini-2-5-pro`) for generating hooks and thumbnail concepts
- **Image Generation**: ⚠️ Not currently functional - `databricks-shutterstock-imageai` endpoint integration exists but is not working

### Content Generation Flow
1. **Hooks**: LLM generates 5 titles + 5 subtitles based on blog content
2. **Thumbnails**: LLM generates thumbnail concepts (TEXT + DESCRIPTION) that can be used as prompts for external image tools
3. Results are displayed in the UI with copy-to-clipboard functionality

### Architecture
- **Frontend**: Dash (Plotly) with Bootstrap components
- **Backend**: Python with MLflow deployment client
- **Asynchronous Processing**: Threading to prevent UI blocking during generation
- **State Management**: Dash stores and intervals for non-blocking updates

