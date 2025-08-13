import os
import json
import logging
import argparse
import requests
from datetime import datetime, timezone # Import timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 1. Setup Logging ---
# Configure logging to be more informative than print()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("conversion.log"), # Log to a file
        logging.StreamHandler() # Also log to the console
    ]
)

# --- Configuration ---
SCOPES = [
    'https://www.googleapis.com/auth/presentations.readonly',
    'https://www.googleapis.com/auth/drive.readonly' # Needed to get modifiedTime
]
STATE_FILE = 'conversion_state.json'

# --- State Management Functions ---
def load_state():
    """Loads the state file that tracks processed presentations."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Saves the current state to the JSON file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- Google API Authentication ---
def get_api_services(credentials_path):
    """Authenticates and returns service objects for Drive and Slides."""
    if not os.path.exists(credentials_path):
        logging.error(f"Credentials file not found at '{credentials_path}'.")
        return None, None
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        drive_service = build('drive', 'v3', credentials=creds)
        slides_service = build('slides', 'v1', credentials=creds)
        logging.info("Authentication successful.")
        return drive_service, slides_service
    except Exception as e:
        logging.error(f"Error during authentication: {e}")
        return None, None

# --- Core Conversion Logic ---
def convert_presentation(drive_service, slides_service, presentation_id, original_path, state):
    """
    Checks modification time, converts a presentation if needed, and updates state.
    """
    try:
        # --- 2a. Check if we need to process this file ---
        logging.info(f"Processing presentation: {os.path.basename(original_path)} (ID: {presentation_id})")
        file_metadata = drive_service.files().get(fileId=presentation_id, fields='id, name, modifiedTime').execute()
        current_modified_time = file_metadata['modifiedTime']
        
        if presentation_id in state:
            last_known_modified_time = state[presentation_id].get('source_modified_timestamp')
            if last_known_modified_time == current_modified_time:
                logging.info("-> SKIPPING: No changes since last conversion.")
                return # Exit this function, no need to process

        logging.info("-> CHANGE DETECTED: Presentation is new or has been updated. Starting conversion...")

        # --- Fetch and convert slides ---
        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])
        
        if not slides:
            logging.warning("The presentation has no slides.")
            return

        logging.info(f"Found {len(slides)} slides to convert.")
        base_output_dir = os.path.dirname(original_path)

        for i, slide in enumerate(slides):
            page_id = slide['objectId']
            slide_number = i + 1
            
            output_folder = os.path.join(base_output_dir, f"Slide {slide_number}")
            os.makedirs(output_folder, exist_ok=True)
            output_filepath = os.path.join(output_folder, f"Slide {slide_number}.png")
            
            thumbnail_request = slides_service.presentations().pages().getThumbnail(
                presentationId=presentation_id,
                pageObjectId=page_id,
                thumbnailProperties_thumbnailSize='LARGE'
            )
            thumbnail_url = thumbnail_request.execute()['contentUrl']

            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                with open(output_filepath, 'wb') as f:
                    f.write(response.content)
                logging.info(f"  -> Successfully saved {output_filepath}")
            else:
                logging.warning(f"  -> FAILED to download slide {slide_number}. Status: {response.status_code}")
        
        # --- 2b. Update the state file upon successful conversion ---
        state[presentation_id] = {
            'local_path': original_path,
            'source_modified_timestamp': current_modified_time,
            # --- FIXED DEPRECATION WARNING ---
            'last_processed_timestamp': datetime.now(timezone.utc).isoformat()
        }
        logging.info(f"-> SUCCESS: Updated state for {presentation_id}.")

    except HttpError as error:
        logging.error(f"An API error occurred for presentation {presentation_id}: {error}")

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Intelligently converts presentations from an input file into PNG slides.')
    parser.add_argument("input_file", help="The .out file generated by find_files_by_type.py.")
    parser.add_argument("-c", "--credentials", required=True, help="Path to your service account credentials JSON file.")
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        logging.error(f"Input file not found at '{args.input_file}'")
        exit()

    drive_service, slides_service = get_api_services(args.credentials)
    if not (drive_service and slides_service):
        exit()

    # Load the current state from the JSON file
    conversion_state = load_state()

    # Process all valid entries in the input file
    with open(args.input_file, 'r', encoding='utf-8') as f:
        # Skip header line
        next(f, None)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2 and parts[0] != "NOT_FOUND":
                target_id = parts[0]
                target_path = parts[1]
                convert_presentation(drive_service, slides_service, target_id, target_path, conversion_state)

    # Save the final, updated state back to the file
    save_state(conversion_state)
    logging.info("Processing complete. Final state saved.")
    