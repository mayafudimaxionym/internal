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
