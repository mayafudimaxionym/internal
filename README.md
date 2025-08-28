<!--
```markdown
-->
# Course Material Automation Pipeline: User Guide

This project provides a unified Python script, `build_module.py`, to automate the entire workflow of creating course materials from a Markdown outline. It handles directory creation, text-to-speech conversion, and Google Slides exporting.

## 1. Prerequisites and One-Time Setup

Before you begin, ensure your environment is set up correctly.

### 1.1. Software
- **Python 3.8+**
- **Google Cloud SDK:** Required for authenticating with Google services.

### 1.2. Python Environment (Virtual Environment)
It is strongly recommended to use a virtual environment to manage project dependencies and avoid conflicts.

```bash
# 1. In your project's root folder, create a virtual environment named 'venv'
python -m venv venv

# 2. Activate it (must be done in every new terminal session)
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install the required Python libraries
pip install -r requirements.txt
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib google-auth requests```

### 1.3. Google Cloud Service Account
For automated access to Google Drive and Slides, a service account is required.

1.  **Create a Service Account:** If you don't have one, create it in the [Google Cloud Console](https://console.cloud.google.com/) under "IAM & Admin" -> "Service Accounts".
2.  **Generate a JSON Key:** Create a key for your service account and download the JSON file.
3.  **Share Your Google Slides:** You must share your Google Slides presentation(s) with the service account's email address (found inside the JSON key file). Grant it **"Viewer"** permissions.

## 2. Configuration Files

The script relies on two external JSON files for configuration.

### 2.1. API Keys (`keys.json`)
To avoid rate-limiting issues, the script supports rotating through multiple Gemini API keys. Create a `keys.json` file with your keys and comments.

**Example `keys.json`:**
```json
[
  {
    "key": "AIzaSy...key_1_here",
    "comment": "Key from primary@gmail.com account"
  },
  {
    "key": "AIzaSy...key_2_here",
    "comment": "Key from secondary@gmail.com account"
  }
]
```

### 2.2. TTS Configuration (`tts_config.json`)
This file controls the text-to-speech model and voice.

**Example `tts_config.json`:**
```json
{
  "model_name": "models/gemini-2.5-flash-preview-tts",
  "prompt_template": "Read in a professional and friendly tone: {}",
  "delay_seconds": 6,
  "generation_config": {
    "response_modalities": ["AUDIO"],
    "speech_config": {
      "voice_config": {
        "prebuilt_voice_config": {
          "voice_name": "Puck"
        }
      }
    }
  }
}
```

## 3. The `course_outline.txt` Format

This file defines the entire structure of your module using strict Markdown hierarchy: `#` for Module, `##` for Video, `###` for Slide, and `-` for Bullet Points.

**Example `course_outline.txt`:**
```markdown
# Module 22: Data-Driven Fraud Detection
## Video 1: Introduction
### Slide 1
- Welcome to our next module.
### Slide 2
- In our previous module, we touched upon how digital fraud has evolved.
```

## 4. Workflow and Commands

All commands should be run from your project's root directory with the virtual environment activated.

### Step 1: `structure`
Parses the outline and creates all necessary folders and `.txt` files.
```bash
py .\build_module.py structure "path/to/Module 22"
```

### Step 2: `tts`
Finds all new or modified `.txt` files and generates a `.wav` audio file for each.```bash
py .\build_module.py tts "path/to/Module 22"
```

### Step 3: `slides`
Finds all `.gslides` files and exports each slide as a `.png` image.
```bash
py .\build_module.py slides "path/to/Module 22" -c "path/to/your/service_account.json"
```

### All-in-One: `build`
Runs `structure`, `tts`, and `slides` sequentially.
```bash
py .\build_module.py build "path/to/Module 22" -c "path/to/your/service_account.json"
```

### NEW: Processing a Specific Video Folder
To save time, you can target a single video folder for `tts` and `slides` operations by using the `--video-folder` argument.

**Example:**
```bash
# This will only generate audio for text files inside "Video 7"
py .\build_module.py tts "path/to/Module 22" --video-folder "Video 7"

# This will only export slides for the .gslides file inside "Video 7"
py .\build_module.py slides "path/to/Module 22" -c "key.json" --video-folder "Video 7"
```

## 5. Advanced Usage & FAQ

### Resuming an Interrupted Process
The script is **resumable**. If a command stops (e.g., due to quota errors), simply **run the same command again**. The script uses a state file (`.build_status.json`) and will automatically skip completed work.

### Updating the Course Outline
If you make a small change to `course_outline.txt`:
1.  Run the `structure` command again to update the `.txt` files.
2.  Run the `tts` command again. It will intelligently **only re-generate audio for the files that actually changed**.

### Expected Output Structure
```
Module 22/
|-- Video 1/
|   |-- Presentation.gslides
|   |-- Slide 1/
|   |   |-- Module_22_video_1_slide_1_bullet_1.txt
|   |   |-- Module_22_video_1_slide_1_bullet_1.wav
|   |   |-- Slide 1.png
|-- .build_status.json
|-- build.structure.log
|-- ... (other logs)
|-- course_outline.txt
```
<!--
```
-->

