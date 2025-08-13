import argparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def check_folder_access(credentials_path):
    """
    Lists all folders accessible to the service account to diagnose permission issues.
    """
    print("Attempting to authenticate...")
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        print("Authentication successful.")
    except Exception as e:
        print(f"Error during authentication: {e}")
        return

    print("\nFetching all accessible folders...")
    try:
        # Query for all folders, not in the trash, that the service account can see.
        # We are not specifying a parent, so it searches everywhere.
        query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        
        response = service.files().list(
            q=query,
            # Add 'sharedWithMe' to the corpus to ensure it checks folders shared with the account
            corpora='allDrives',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='files(id, name, parents, sharedWithMeTime)'
        ).execute()
        
        folders = response.get('files', [])

        if not folders:
            print("\n-> RESULT: No folders found. The service account does not have access to any folders.")
        else:
            print(f"\n-> RESULT: Found {len(folders)} accessible folder(s):")
            for folder in folders:
                print(f"  - Name: '{folder.get('name')}'")
                print(f"    ID: {folder.get('id')}")
                # The 'parents' field tells us where the folder is located.
                # If it's a top-level shared folder, it might not have a parent in 'My Drive'.
                print(f"    Parent IDs: {folder.get('parents')}")
                print("-" * 20)

    except HttpError as error:
        print(f"An API error occurred: {error}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lists all folders a service account can access.')
    parser.add_argument("-c", "--credentials", required=True, help="Path to your service account credentials JSON file.")
    args = parser.parse_args()
    
    check_folder_access(args.credentials)
    