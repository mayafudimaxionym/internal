# build_module.py

# --- Standard Library Imports ---
import os
import argparse
import json
import logging
import time
import hashlib
import re
import wave

# --- Third-Party Library Imports ---
import google.generativeai as genai
import requests
from tqdm import tqdm

# --- Google Authentication and API Client Imports ---
from google.oauth2 import service_account
from googleapiclient.discovery import build as google_api_build


# --- State Management Functions ---
def load_state(module_path):
    """Loads the build state from .build_status.json."""
    state_file = os.path.join(module_path, ".build_status.json")
    if not os.path.exists(state_file): return {"files": {}, "key_stats": {}}
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
            if "key_stats" not in state: state["key_stats"] = {}
            return state
    except (json.JSONDecodeError, IOError): return {"files": {}, "key_stats": {}}

def save_state(module_path, state):
    """Saves the current build state to .build_status.json."""
    state_file = os.path.join(module_path, ".build_status.json")
    with open(state_file, 'w', encoding='utf-8') as f: json.dump(state, f, indent=2)

def get_file_hash(file_path):
    """Computes the SHA-256 hash of a file's content."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192): sha256.update(chunk)
        return sha256.hexdigest()
    except IOError: return None

# --- Logger Setup ---
def setup_logger(module_path, command):
    """Configures a logger for a specific command."""
    log_filename = f"build.{command}.log"
    log_file = os.path.join(module_path, log_filename)
    logger = logging.getLogger("CourseBuilder")
    if logger.hasHandlers(): logger.handlers.clear()
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(ch)
    return logger

# --- Helper Functions ---
def sanitize_filename(name):
    """Sanitizes a string to be a valid filename."""
    name = re.sub(r'[:]', '-', name)
    name = re.sub(r'[\\/*?"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name

def parse_outline(file_path, logger):
    """Parses a Markdown-formatted course outline into a structured dictionary."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    except FileNotFoundError: logger.error(f"Outline file not found at {file_path}"); return None
    except Exception as e: logger.error(f"An error occurred reading outline: {e}"); return None
    structure = {"module_title": "", "videos": []}
    current_video, current_slide = None, None
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('# '): structure["module_title"] = line[2:].strip()
        elif line.startswith('## '): current_video = {"title": line[3:].strip(), "slides": []}; structure["videos"].append(current_video)
        elif line.startswith('### '):
            if current_video is None: continue
            current_slide = {"title": line[4:].strip(), "bullets": []}; current_video["slides"].append(current_slide)
        elif line.startswith('- '):
            if current_slide is None: continue
            current_slide["bullets"].append(line[2:].strip())
    return structure

# --- Command-Specific Functions ---
def load_tts_config(logger):
    """Loads TTS model and voice configuration from tts_config.json."""
    config_path = "tts_config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
        voice = config.get('generation_config', {}).get('speech_config', {}).get('voice_config', {}).get('prebuilt_voice_config', {}).get('voice_name')
        logger.info(f"Loaded TTS config from {config_path} (model: {config.get('model_name')}, voice: {voice})")
        return config
    except Exception as e: logger.error(f"Error loading {config_path}: {e}"); return None

def load_api_keys(logger):
    """Loads API keys from keys.json, expecting a list of objects with "key" and "comment"."""
    keys_path = "keys.json"
    try:
        with open(keys_path, 'r', encoding='utf-8') as f: key_objects = json.load(f)
        if not isinstance(key_objects, list) or not key_objects: raise ValueError("keys.json must be a non-empty list of objects.")
        extracted_keys = [item['key'] for item in key_objects if 'key' in item and item['key']]
        if not extracted_keys: raise ValueError("No valid 'key' fields found in keys.json.")
        logger.info(f"Loaded {len(extracted_keys)} API keys from {keys_path}.")
        return extracted_keys
    except Exception as e: logger.error(f"Error reading {keys_path}: {e}"); return None

def generate_audio(model, prompt, config):
    """Generates audio using the model.generate_content method."""
    try:
        response = model.generate_content(contents=[prompt], generation_config=config.get("generation_config", {}))
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception as e: return f"API Error: {e}"

def get_google_api_services(logger, credentials_path):
    """Authenticates using a service account JSON file and builds API services."""
    SCOPES = ['https://www.googleapis.com/auth/presentations.readonly', 'https://www.googleapis.com/auth/drive.readonly']
    if not os.path.exists(credentials_path):
        logger.error(f"FATAL: Service account key file not found: '{credentials_path}'"); return None, None
    try:
        creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        drive_service = google_api_build('drive', 'v3', credentials=creds)
        slides_service = google_api_build('slides', 'v1', credentials=creds)
        logger.info("Successfully authenticated using service account file.")
        return drive_service, slides_service
    except Exception as e: logger.error(f"Failed to authenticate with service account: {e}"); return None, None

def get_all_slides_map(drive_service, logger):
    """Fetches all presentations visible to the service account and returns a map."""
    logger.info("Fetching a list of all accessible presentations from Google Drive...")
    slides_map = {}
    page_token = None
    try:
        while True:
            response = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.presentation' and trashed = false",
                spaces='drive', fields='nextPageToken, files(id, name, modifiedTime)',
                corpora='allDrives', includeItemsFromAllDrives=True, supportsAllDrives=True,
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                slides_map[file['name']] = {'id': file['id'], 'modifiedTime': file['modifiedTime']}
            page_token = response.get('nextPageToken', None)
            if page_token is None: break
        logger.info(f"Found {len(slides_map)} total presentations on Google Drive.")
        return slides_map
    except Exception as e:
        logger.error(f"An API error occurred while listing presentations: {e}")
        return None

def normalize_name(name):
    """Normalizes a filename for robust comparison by removing special chars."""
    name = name.lower()
    name = name.replace(':', '')
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

# --- Main Command Functions ---
def run_structure(args, logger):
    """Parses the outline, creates directories and .txt files. Returns True on success, False on failure."""
    logger.info("--- Starting: Structure Generation ---")
    start_time = time.time()
    outline_file = os.path.join(args.module_path, "course_outline.txt")
    course_data = parse_outline(outline_file, logger)
    if not course_data:
        logger.error("Failed to parse course outline.")
        return False
    logger.info(f"Successfully parsed outline for module: '{course_data['module_title']}'")
    video_dirs_created, slide_dirs_created, files_created = 0, 0, 0
    module_name_sanitized = sanitize_filename(course_data['module_title'])
    for video_idx, video in enumerate(course_data["videos"], 1):
        video_path = os.path.join(args.module_path, f"Video {video_idx}")
        if not os.path.exists(video_path):
            os.makedirs(video_path, exist_ok=True); video_dirs_created += 1
        for slide_idx, slide in enumerate(video["slides"], 1):
            slide_path = os.path.join(video_path, f"Slide {slide_idx}")
            if not os.path.exists(slide_path):
                os.makedirs(slide_path, exist_ok=True); slide_dirs_created += 1
            for bullet_idx, bullet in enumerate(slide["bullets"], 1):
                file_name = f"{module_name_sanitized}_video_{video_idx}_slide_{slide_idx}_bullet_{bullet_idx}.txt"
                file_path = os.path.join(slide_path, file_name)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f: f.write(bullet)
                    files_created += 1
                except IOError as e: logger.error(f"Failed to write file {file_path}: {e}")
    end_time = time.time()
    logger.info(f"Summary: Created {video_dirs_created} Video folders, {slide_dirs_created} Slide folders, and {files_created} text files.")
    logger.info(f"--- Finished: Structure Generation in {end_time - start_time:.2f} seconds ---")
    return True



def run_build(args, logger):
    """Runs the full build process, stopping if any step fails."""
    logger.info("--- Starting: Full Build Process ---")
    start_time = time.time()
    if not run_structure(args, logger):
        logger.error("Build process stopped due to failure in 'structure' step."); return
    if not run_tts(args, logger):
        logger.error("Build process stopped due to failure in 'tts' step."); return
    if hasattr(args, 'credentials') and args.credentials:
        if not run_slides(args, logger):
            logger.error("Build process stopped due to failure in 'slides' step."); return
    else:
        logger.warning("Skipping slides step in full build: --credentials path not provided.")
    end_time = time.time()
    logger.info(f"--- Full Build Process Finished in {end_time - start_time:.2f} seconds ---")

def run_list_slides(args, logger):
    """[DIAGNOSTIC] Lists all presentation files visible to the service account."""
    logger.info("--- Starting: List All Visible Slides (Diagnostic) ---")
    drive_service, _ = get_google_api_services(logger, args.credentials)
    if not drive_service: logger.error("Could not authenticate. Aborting."); return
    try:
        logger.info("Fetching all accessible presentations from Google Drive...")
        all_presentations = []
        page_token = None
        while True:
            response = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.presentation' and trashed = false",
                spaces='drive', fields='nextPageToken, files(id, name)',
                corpora='allDrives', includeItemsFromAllDrives=True, supportsAllDrives=True,
                pageToken=page_token
            ).execute()
            all_presentations.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None: break
        if not all_presentations:
            logger.warning("No Google Slides presentations were found for this service account.")
        else:
            logger.info(f"Found {len(all_presentations)} presentations. Names are listed below:")
            for pres in sorted(all_presentations, key=lambda x: x['name']):
                print(f"  - '{pres['name']}'")
    except Exception as e:
        logger.error(f"An API error occurred while listing files: {e}")

# --- Main CLI Entry Point ---
def main():
    """Defines the command-line interface and executes the chosen command."""
    parser = argparse.ArgumentParser(description="Build course materials from an outline.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("module_path", type=str, help="Path to the module directory.")
    sp_structure = subparsers.add_parser("structure", help="Generate directory structure.", parents=[parent_parser])
    sp_structure.set_defaults(func=run_structure)
    video_folder_parser = argparse.ArgumentParser(add_help=False)
    video_folder_parser.add_argument("--video-folder", type=str, help="Target a specific video folder.")
    sp_tts = subparsers.add_parser("tts", help="Generate audio files.", parents=[parent_parser, video_folder_parser])
    sp_tts.set_defaults(func=run_tts)
    sp_slides = subparsers.add_parser("slides", help="Export Google Slides.", parents=[parent_parser, video_folder_parser])
    sp_slides.add_argument("-c", "--credentials", required=True, help="Path to service account JSON file.")
    sp_slides.set_defaults(func=run_slides)
    sp_build = subparsers.add_parser("build", help="Run the full build process.", parents=[parent_parser, video_folder_parser])
    sp_build.add_argument("-c", "--credentials", help="Path to credentials for the slides step.")
    sp_build.set_defaults(func=run_build)
    sp_list = subparsers.add_parser("list-slides", help="[DIAGNOSTIC] List visible presentations.", parents=[parent_parser])
    sp_list.add_argument("-c", "--credentials", required=True, help="Path to service account JSON file.")
    sp_list.set_defaults(func=run_list_slides)
    args = parser.parse_args()
    if not os.path.isdir(args.module_path):
        print(f"Error: Module directory not found: '{args.module_path}'"); return
    logger = setup_logger(args.module_path, args.command)
    args.func(args, logger)

if __name__ == "__main__":
    main()

    