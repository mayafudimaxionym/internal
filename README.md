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
# 1. Create a virtual environment named 'venv' in your scripts folder
python -m venv venv

# 2. Activate it (must be done in every new terminal session)
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install the required Python libraries
pip install -r requirements.txt
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib google-auth requests


### 1.3. Google Cloud Service Account
For automated access to Google Drive and Slides, a service account is required. This is more secure and reliable than personal user authentication for scripts.

1.  **Create a Service Account:** If you don't have one, create it in the [Google Cloud Console](https://console.cloud.google.com/) under "IAM & Admin" -> "Service Accounts".
2.  **Generate a JSON Key:** Create a key for your service account and download the JSON file.
3.  **Share Your Google Slides:** The most crucial step. You must share your Google Slides presentation(s) with the service account's email address (found inside the JSON key file, e.g., `...gserviceaccount.com`). Grant it **"Viewer"** permissions.

## 2. Configuration Files

The script relies on two external JSON files for configuration.

### 2.1. Service Account Key
This is the JSON file you downloaded from Google Cloud. You can name it whatever you like (e.g., `tts.json`) and provide its path to the script when running the `slides` or `build` command.

### 2.2. TTS Configuration (`tts_config.json`)
This file controls the text-to-speech model and voice. It must be in the same directory as `build_module.py`.

**Example `tts_config.json`:**
json
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
- **`model_name`**: The specific Gemini model to use for TTS.
- **`prompt_template`**: A string used to format the text before sending it to the API. The `{}` will be replaced with the text from your bullet points.
- **`delay_seconds`**: The pause between API calls to avoid rate-limiting errors. A value of `6` allows for 10 requests per minute.
- **`generation_config`**: Advanced settings, including the voice name (`Puck`).

## 3. The `course_outline.txt` Format

This is the master file that defines the entire structure of your module. It must follow a strict Markdown hierarchy:

-   `# Module Title`: There should be only one H1 tag for the module title.
-   `## Video Title`: An H2 tag for each video.
-   `### Slide Title`: An H3 tag for each slide within a video.
-   `- Bullet Point`: An unordered list item for each piece of narration on a slide.

**Example `course_outline.txt`:**
```markdown 
# Module 22: Data-Driven Fraud Detection
## Video 1: Introduction
### Slide 1
- Welcome to our next module.
### Slide 2
- In our previous module, we touched upon how digital fraud has evolved.
- This new breed of fraudster leverages sophisticated tools.
```

## 4. Step-by-Step Workflow

Follow these steps to generate a complete module.

### Step 1: Prepare Your Module Directory
1.  Create your main module folder (e.g., `Module 22`).
2.  Inside it, create your `course_outline.txt` file with the correct format.
3.  Create sub-folders for each video (e.g., `Video 1`, `Video 2`).
4.  Place the corresponding Google Slides shortcut file (`.gslides`) inside each `Video` folder.

### Step 2: Run the `structure` command
This command parses your outline and creates all the necessary sub-folders (`Slide 1`, `Slide 2`, etc.) and the text files for narration (`.txt`).

```bash
# Make sure your venv is active
(venv) py .\build_module.py structure "path/to/Module 22"
```

### Step 3: Run the `tts` command
This command finds all new or modified `.txt` files and generates a `.wav` audio file for each.

```bash
# Set your Gemini API key in your terminal
# On Windows (PowerShell):
$env:GOOGLE_API_KEY="your_api_key_here"

# Run the command
(venv) py .\build_module.py tts "path/to/Module 22"
```

### Step 4: Run the `slides` command
This command finds all `.gslides` files, connects to the Google Drive API, and exports each slide as a `.png` image into the correct `Slide` folder.

```bash
(venv) py .\build_module.py slides "path/to/Module 22" -c "path/to/your/tts.json"
```

### All-in-One: The `build` command
To run all three steps sequentially, use the `build` command.

```bash
(venv) py .\build_module.py build "path/to/Module 22" -c "path/to/your/tts.json"
```

## 5. Advanced Usage & FAQ

### How do I resume the process if it's interrupted?
The script is **idempotent and resumable**. If a command (like `tts` or `slides`) stops due to a quota error or any other issue, simply **run the same command again**. The script uses a state file (`.build_status.json`) to track completed work and will automatically skip files that were already processed successfully, continuing from where it left off.

### What if I make a small change to `course_outline.txt`?
You do not need to re-process everything. The correct workflow is:
1.  Make your changes in `course_outline.txt`.
2.  Run the `structure` command again. This will overwrite the `.txt` files, updating only those that have changed content.
3.  Run the `tts` command again. The script will calculate the hash of each `.txt` file. It will see that only a few files have new hashes (because their content changed) and will **only re-generate audio for those specific files**, skipping all the others.

### Expected Output Structure

After running the full build, your directory will look like this:

```
Module 22/
|-- Video 1/
|   |-- Module22_Video1_Title.gslides
|   |-- Slide 1/
|   |   |-- Module_22_video_1_slide_1_bullet_1.txt
|   |   |-- Module_22_video_1_slide_1_bullet_1.wav
|   |   |-- Slide 1.png
|   |-- Slide 2/
|   |   |-- ...
|-- Video 2/
|   |-- ...
|-- .build_status.json
|-- build.structure.log
|-- build.tts.log
|-- build.slides.log
|-- course_outline.txt
```