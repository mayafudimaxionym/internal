# Gemini TTS Converter

This script recursively converts text files (`.txt`) to WAV audio files (`.wav`) using the Google Gemini Pro API.

## Features

-   **Recursive Conversion**: The script searches for `.txt` files in the specified folder and all its subdirectories.
-   **Incremental Conversion**: Only converts `.txt` files that are new or have been modified since the last conversion.
-   **Logging**: Logs all operations to both the console and a `tts_converter.log` file for easy debugging and tracking.

## Prerequisites

-   Python 3.6+
-   A Google API key with the Gemini Pro API enabled.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mayafudimaxionym/internal.git
    ```
2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up your Google API key:**
    Set the `GOOGLE_API_KEY` environment variable to your Google API key.
    -   **Windows:**
        ```bash
        setx GOOGLE_API_KEY "YOUR_API_KEY"
        ```
    -   **Linux/macOS:**
        ```bash
        export GOOGLE_API_KEY="YOUR_API_KEY"
        ```

## Usage

To run the script, use the following command:

```bash
python gemini-tts-converter.py "path/to/your/folder"
```

Replace `"path/to/your/folder"` with the full path to the folder containing your `.txt` files.

### Example

```bash
python gemini-tts-converter.py "h:\My Drive\Consulting\Udemy Course\Fraud Fundamentals Course\Module 2\Video 3\"
```

## Logging

The script logs all its actions to the console and to a file named `tts_converter.log` in the same directory as the script. The log file is automatically created and appended to on each run. The `tts_converter.log` file is ignored by Git.

---

## Project Files Overview

This repository contains various scripts and configuration files related to the "Fraud Fundamentals Course".

### Core Scripts

*   `gemini-tts-converter.py`: (Main script) Converts text files to audio using Gemini Pro API.
*   `tts_converter.py`: Likely a core module or an older version related to TTS conversion.
*   `convert_slides.py`: This script intelligently converts Google Slides presentations into PNG images. It authenticates with Google Drive and Slides APIs, checks the modification time of presentations to avoid redundant conversions, and saves each slide as a high-quality PNG in a structured output directory. It also manages conversion state to track processed presentations.
*   `find_files_by_type.py`: This script is designed to locate Google Slides presentations by matching local filenames (e.g., `.pptx` files) with their corresponding IDs in Google Drive. It authenticates with the Google Drive API, fetches a map of all accessible Google Slides, and outputs a file (`find_files_by_type.out`) containing the Google Drive ID and local path for each matched presentation. This output file can then be used as input for other scripts like `convert_slides.py`.
*   `check_permissions.py`: A script likely used to verify file or directory permissions.
*   `create_structure.py`: A script to create a specific directory or file structure.
*   `process_outline.py`: A script for processing course outlines or similar structured text.
*   `convert_videos.bat`: A Windows batch script for video conversion tasks.

### Data & Configuration

*   `Calculate Activity Rate Change.ipynb`: A Jupyter Notebook, likely for data analysis or calculations related to activity rate changes.
*   `requirements.txt`: Lists the Python dependencies required for the project.
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore.

---

## Google Slides to PNG Conversion Pipeline

This project contains a two-script Python pipeline designed to automate the conversion of native Google Slides presentations into high-quality PNG images for each slide. It's built to be intelligent, keeping track of which files have been processed and only re-processing them if they have been updated in Google Drive.

### Key Features
*   **Automated Discovery**: Scans a local directory structure and finds the corresponding native Google Slides presentations in your Google Drive.
*   **Intelligent Conversion**: Only processes new presentations or those that have been modified since the last run.
*   **High-Quality Output**: Generates large-format PNG images for the best quality.
*   **Organized Structure**: Saves each slide's PNG into a dedicated, numbered sub-folder (e.g., `Slide 1/Slide 1.png`).
*   **State Management**: Remembers the last-processed state in a `conversion_state.json` file.
*   **Detailed Logging**: Records all actions, successes, and errors into a `conversion.log` file for easy troubleshooting.

### Prerequisites
Before running the scripts, ensure you have the following set up:

*   **Python 3**: With the required libraries installed. You can install them all by running:
    ```bash
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
    ```
*   **Google Cloud Project**: A project set up in the Google Cloud Console.
*   **APIs Enabled**: In your Google Cloud project, make sure both the Google Drive API and Google Slides API are enabled.
*   **Service Account**: A service account created in your project with a downloadable JSON key file (e.g., `tts.json`).
*   **Folder Sharing**: The top-level folder in your Google Drive that contains the presentations (e.g., the Consulting folder) must be shared with the service account's `client_email` address, giving it at least Viewer permissions.

### The Scripts
This pipeline consists of two main scripts that should be run in order.

#### 1. `find_files_by_type.py`
This script is responsible for discovery. It walks through your local file directory, finds files with a specific extension (e.g., `.pptx`), and then searches your Google Drive for a native Google Slides presentation with the same name. It outputs a sorted list of found IDs and their corresponding local paths to `find_files_by_type.out`.

**Usage:**
```bash
py find_files_by_type.py "[LOCAL_SEARCH_PATH]" .pptx "[GDRIVE_ROOT_PATH]" -c [CREDENTIALS_FILE]
```

**Example:**
```bash
py find_files_by_type.py "H:\My Drive\Consulting\Udemy Course" .pptx "H:\My Drive" -c tts.json
```

#### 2. `convert_slides.py`
This script performs the conversion. It reads the `find_files_by_type.out` file, checks each presentation against its memory (`conversion_state.json`), and if the presentation is new or updated, it connects to the Google Slides API to download each slide as a PNG.

**Usage:**
```bash
py convert_slides.py find_files_by_type.out -c [CREDENTIALS_FILE]
```

**Example:**
```bash
py convert_slides.py find_files_by_type.out -c tts.json
```

### Complete Workflow
Here is the step-by-step process for running the full pipeline:

1.  Ensure your local files and Google Drive are synced and that your Google Slides have been saved in their native format.
2.  Run the finder script to discover the presentation IDs and create the `.out` file.
    ```bash
    py find_files_by_type.py "H:\My Drive\Consulting\Udemy Course" .pptx "H:\My Drive" -c tts.json
    ```
3.  Run the converter script to process the list of files.
    ```bash
    py convert_slides.py find_files_by_type.out -c tts.json
    ```
4.  Review the output: Check your local folders for the generated PNG images and review `conversion.log` for a detailed report of the process.

If you run the converter script again immediately, it will skip all presentations because their modification time hasn't changed. If you update a presentation in Google Slides and run the scripts again, only that specific presentation will be re-processed.