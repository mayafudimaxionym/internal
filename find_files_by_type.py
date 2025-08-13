import os
import re
import argparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# --- Google Drive Authentication ---
def get_drive_service(credentials_path):
    """Authenticates with Google Drive API using a service account JSON file."""
    if not os.path.exists(credentials_path):
        print(f"ERROR: Credentials file not found at '{credentials_path}'.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        print("Authentication successful using service account.")
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None

# --- More Robust Core Logic ---
def get_all_slides_map(service):
    """
    Fetches all Google Slides accessible by the service account and returns a
    dictionary mapping their names to their IDs.
    """
    print("Fetching a list of all accessible Google Slides from Drive...")
    slides_map = {}
    page_token = None
    try:
        while True:
            response = service.files().list(
                q="mimeType='application/vnd.google-apps.presentation' and trashed = false",
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                corpora='allDrives',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageToken=page_token
            ).execute()
            
            for file in response.get('files', []):
                if file['name'] not in slides_map:
                    slides_map[file['name']] = []
                slides_map[file['name']].append(file['id'])
                
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        print(f"Found {len(slides_map)} unique presentation names.")
        return slides_map
    except HttpError as error:
        print(f"An API error occurred while fetching slides list: {error}")
        return None

# --- Helper function for natural sorting ---
def natural_sort_key(s):
    """Create a key for natural sorting."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Finds native Google Slides IDs by matching filenames.')
    parser.add_argument("search_path", help="The local directory to start the search from.")
    parser.add_argument("extension", help="The local file extension to look for (e.g., .pptx).")
    parser.add_argument("drive_root", help=r"The local path to your Google Drive root folder (e.g., 'H:\My Drive').")
    parser.add_argument("-c", "--credentials", required=True, help="Path to your service account credentials JSON file.")
    args = parser.parse_args()

    service = get_drive_service(args.credentials)
    if not service:
        exit()

    slides_id_map = get_all_slides_map(service)
    if slides_id_map is None:
        print("Could not retrieve slide map from Google Drive. Aborting.")
        exit()

    # --- NEW DEBUGGING STEP ---
    print("\n--- DEBUG: Accessible Google Slide Names ---")
    if not slides_id_map:
        print("The map is empty. No Google Slides were found.")
    else:
        for name in sorted(slides_id_map.keys()):
            print(f"  - '{name}'")
    print("--- END DEBUG ---\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = "find_files_by_type.out"
    output_filepath = os.path.join(script_dir, output_filename)

    if not os.path.isdir(args.search_path):
        print(f"Error: The path '{args.search_path}' is not a valid directory.")
    else:
        local_files = []
        for dirpath, _, filenames in os.walk(args.search_path):
            for filename in filenames:
                if filename.startswith('~$'): continue
                if filename.endswith(args.extension):
                    local_files.append(os.path.join(dirpath, filename))
        
        all_results = []
        if local_files:
            print(f"\nMatching {len(local_files)} local files to the Google Slides map...")
            for file_path in local_files:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                found_ids = slides_id_map.get(base_name)
                drive_id = "NOT_FOUND"
                if found_ids:
                    drive_id = found_ids[0]
                    if len(found_ids) > 1:
                        print(f"  - WARNING: Found multiple slides named '{base_name}'. Using the first one found (ID: {drive_id}).")

                all_results.append({
                    "id": drive_id,
                    "path": file_path
                })
            
            print("\nSorting results...")
            all_results.sort(key=lambda item: natural_sort_key(item['path']))
            
            print(f"Writing sorted results to {output_filepath}...")
            with open(output_filepath, 'w', encoding='utf-8') as f_out:
                f_out.write("FileID\tPath/filename\n")
                for result in all_results:
                    f_out.write(f"{result['id']}\t{result['path']}\n")
            print("\nProcessing complete.")
        else:
            print(f"No files with the '{args.extension}' extension found in '{args.search_path}'.")