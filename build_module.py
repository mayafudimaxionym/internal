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
    """
    Loads the build state from .build_status.json in the module directory.
    The state file tracks processed files (by hash or timestamp) and API key usage.
    """
    state_file = os.path.join(module_path, ".build_status.json")
    if not os.path.exists(state_file):
        return {"files": {}, "key_stats": {}}
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
            # Ensure key_stats exists for backward compatibility with older state files.
            if "key_stats" not in state:
                state["key_stats"] = {}
            return state
    except (json.JSONDecodeError, IOError):
        return {"files": {}, "key_stats": {}}

def save_state(module_path, state):
    """Saves the current build state to .build_status.json."""
    state_file = os.path.join(module_path, ".build_status.json")
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def get_file_hash(file_path):
    """Computes the SHA-256 hash of a file's content for change detection."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except IOError:
        return None

# --- Logger Setup ---

def setup_logger(module_path, command):
    """
    Configures a logger to output to both the console and a command-specific file.
    The log file is overwritten on each run to keep it clean.
    """
    log_filename = f"build.{command}.log"
    log_file = os.path.join(module_path, log_filename)
    
    logger = logging.getLogger("CourseBuilder")
    if logger.hasHandlers():
        logger.handlers.clear()
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
    """Sanitizes a string to be a valid filename (replaces spaces with underscores)."""
    name = re.sub(r'[:]', '-', name)
    name = re.sub(r'[\\/*?"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name

def sanitize_directory_name(name):
    """Sanitizes a string to be a valid directory name (preserves spaces)."""
    name = re.sub(r'[:]', '-', name)
    name = re.sub(r'[\\/*?"<>|]', '', name)
    return name.strip()

def parse_outline(file_path, logger):
    """Parses a Markdown-formatted course outline into a structured dictionary."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        logger.error(f"Outline file not found at {file_path}"); return None
    except Exception as e:
        logger.error(f"An error occurred reading the outline file: {e}"); return None

    structure = {"module_title": "", "videos": []}
    current_video, current_slide = None, None
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('# '): structure["module_title"] = line[2:].strip()
        elif line.startswith('## '):
            current_video = {"title": line[3:].strip(), "slides": []}
            structure["videos"].append(current_video)
        elif line.startswith('### '):
            if current_video is None: continue
            current_slide = {"title": line[4:].strip(), "bullets": []}
            current_video["slides"].append(current_slide)
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
    except FileNotFoundError: logger.error(f"Configuration file not found: {config_path}"); return None
    except json.JSONDecodeError: logger.error(f"Error decoding JSON from {config_path}"); return None

def load_api_keys(logger):
    """
    Loads API keys from keys.json, expecting a list of objects with "key" and "comment".
    """
    keys_path = "keys.json"
    try:
        with open(keys_path, 'r', encoding='utf-8') as f:
            key_objects = json.load(f)
        if not isinstance(key_objects, list) or not key_objects:
            raise ValueError("keys.json should contain a non-empty list of objects.")
        
        # Extract only the key string from each object.
        extracted_keys = [item['key'] for item in key_objects if 'key' in item and item['key']]
        if not extracted_keys:
            raise ValueError("No valid 'key' fields found in the objects in keys.json.")

        logger.info(f"Loaded {len(extracted_keys)} API keys from {keys_path}.")
        return extracted_keys
    except FileNotFoundError:
        logger.error(f"API keys file not found: {keys_path}. Please create it."); return None
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error reading {keys_path}: {e}"); return None

def generate_audio(model, prompt, config):
    """Generates audio by replicating the working logic from gemini-tts-converter.py."""
    try:
        response = model.generate_content(
            contents=[prompt],
            generation_config=config.get("generation_config", {})
        )
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception as e:
        return f"API Error: {e}"

def get_google_api_services(logger, credentials_path):
    """Authenticates using a service account JSON file and builds API services."""
    SCOPES = ['https://www.googleapis.com/auth/presentations.readonly', 'https://www.googleapis.com/auth/drive.readonly']
    if not os.path.exists(credentials_path):
        logger.error(f"FATAL: Service account key file not found at '{credentials_path}'"); return None, None
    try:
        creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        drive_service = google_api_build('drive', 'v3', credentials=creds)
        slides_service = google_api_build('slides', 'v1', credentials=creds)
        logger.info("Successfully authenticated using service account file.")
        return drive_service, slides_service
    except Exception as e:
        logger.error(f"Failed to authenticate using service account: {e}"); return None, None

# --- Main Command Functions ---

def run_structure(args, logger):
    """Parses the outline and creates the directory structure and text files."""
    logger.info("--- Starting: Structure Generation ---")
    start_time = time.time()
    
    outline_file = os.path.join(args.module_path, "course_outline.txt")
    course_data = parse_outline(outline_file, logger)
    if not course_data:
        logger.error("Failed to parse course outline."); return

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

def run_tts(args, logger):
    """Finds all .txt files and converts them to .wav audio using multiple API keys."""
    logger.info("--- Starting: Text-to-Speech Conversion ---")
    start_time = time.time()

    api_keys = load_api_keys(logger)
    if not api_keys: return

    tts_config = load_tts_config(logger)
    if not tts_config: return

    model_name = tts_config.get("model_name")
    prompt_template = tts_config.get("prompt_template", "{}")
    delay = tts_config.get("delay_seconds", 5)

    state = load_state(args.module_path)
    
    key_stats = state.get("key_stats", {})
    for i in range(len(api_keys)):
        if f"key_{i}" not in key_stats: key_stats[f"key_{i}"] = 0
    
    # Determine the search path. If --video-folder is specified, scan only that folder.
    search_path = args.module_path
    if hasattr(args, 'video_folder') and args.video_folder:
        specific_folder_path = os.path.join(args.module_path, args.video_folder)
        if not os.path.isdir(specific_folder_path):
            logger.error(f"Specified video folder not found: {specific_folder_path}"); return
        search_path = specific_folder_path
        logger.info(f"Processing in targeted mode: only scanning folder '{args.video_folder}'.")

    files_to_process, skipped_files, total_files = [], 0, 0
    for root, _, files in os.walk(search_path):
        for file in files:
            if file.endswith(".txt") and "course_outline" not in file:
                total_files += 1
                file_path = os.path.join(root, file)
                current_hash = get_file_hash(file_path)
                relative_path = os.path.relpath(file_path, args.module_path)
                if state["files"].get(relative_path) == current_hash:
                    skipped_files += 1
                else:
                    files_to_process.append((file_path, current_hash))

    logger.info(f"Found {total_files} total text files. {len(files_to_process)} to process, {skipped_files} already up to date.")

    converted_count, failed_count, key_index = 0, 0, 0
    if files_to_process:
        for file_path, file_hash in tqdm(files_to_process, desc="Converting text to speech"):
            try:
                # Rotate through the available keys for each request to distribute load.
                current_key_name = f"key_{key_index}"
                genai.configure(api_key=api_keys[key_index])
                tts_model = genai.GenerativeModel(model_name)
                
                with open(file_path, 'r', encoding='utf-8') as f: text_content = f.read()
                if not text_content.strip():
                    logger.warning(f"Skipping empty file: {file_path}"); continue

                prompt = prompt_template.format(text_content)
                audio_data = generate_audio(tts_model, prompt, tts_config)

                if isinstance(audio_data, bytes):
                    output_path = os.path.splitext(file_path)[0] + ".wav"
                    with wave.open(output_path, "wb") as wf:
                        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000); wf.writeframes(audio_data)

                    relative_path = os.path.relpath(file_path, args.module_path)
                    state["files"][relative_path] = file_hash
                    converted_count += 1
                    
                    key_stats[current_key_name] += 1
                    logger.info(f"Success with {current_key_name} for {os.path.basename(file_path)}. Pausing for {delay} sec...")
                    key_index = (key_index + 1) % len(api_keys)
                    
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to convert {file_path} with {current_key_name}: {audio_data}")
                    failed_count += 1
            except Exception as e:
                logger.error(f"An unexpected error with {current_key_name} on {file_path}: {e}")
                failed_count += 1

    state["key_stats"] = key_stats
    save_state(args.module_path, state)
    
    end_time = time.time()
    logger.info(f"Summary: {converted_count} files converted, {failed_count} failed, {skipped_files} skipped.")
    logger.info(f"Key Usage Statistics: {json.dumps(key_stats)}")
    logger.info(f"--- Finished: Text-to-Speech Conversion in {end_time - start_time:.2f} seconds ---")

def run_slides(args, logger):
    """Finds .gslides files and exports their pages as PNG images."""
    logger.info("--- Starting: Google Slides Export ---")
    start_time = time.time()

    drive_service, slides_service = get_google_api_services(logger, args.credentials)
    if not drive_service or not slides_service: return

    state = load_state(args.module_path)
    
    # Determine search path, supporting targeted folder processing.
    search_path = os.path.abspath(args.module_path)
    if hasattr(args, 'video_folder') and args.video_folder:
        specific_folder_path = os.path.join(search_path, args.video_folder)
        if not os.path.isdir(specific_folder_path):
            logger.error(f"Specified video folder not found: {specific_folder_path}"); return
        search_path = specific_folder_path
        logger.info(f"Processing in targeted mode: only scanning folder '{args.video_folder}'.")
    else:
        logger.info(f"Scanning for presentations in absolute path: {search_path}")

    presentations_to_process, skipped_count = [], 0
    
    for root, _, files in os.walk(search_path):
        for file in files:
            if file.endswith(".gslides"):
                gslides_path = os.path.join(root, file)
                try:
                    base_name = os.path.splitext(file)[0]
                    query = f"name = '{base_name}' and mimeType = 'application/vnd.google-apps.presentation' and trashed = false"
                    response = drive_service.files().list(
                        q=query, spaces='drive', fields='files(id, name, modifiedTime)',
                        corpora='allDrives', includeItemsFromAllDrives=True, supportsAllDrives=True
                    ).execute()
                    
                    if not response['files']:
                        logger.warning(f"Could not find presentation '{base_name}' on Google Drive. Skipping.")
                        continue
                    
                    drive_file = response['files'][0]
                    presentation_id, remote_mod_time = drive_file['id'], drive_file['modifiedTime']
                    
                    relative_path = os.path.relpath(gslides_path, os.path.abspath(args.module_path))
                    if state["files"].get(relative_path) == remote_mod_time:
                        skipped_count += 1
                        logger.info(f"Skipping '{file}': remote version is unchanged.")
                    else:
                        presentations_to_process.append((gslides_path, presentation_id, remote_mod_time))
                except Exception as e:
                    logger.error(f"Failed to process or find metadata for {file}: {e}")

    logger.info(f"Found {len(presentations_to_process) + skipped_count} presentations. {len(presentations_to_process)} to process, {skipped_count} up to date.")

    exported_slides, failed_slides = 0, 0
    for gslides_path, pres_id, mod_time in tqdm(presentations_to_process, desc="Exporting slides"):
        try:
            presentation = slides_service.presentations().get(presentationId=pres_id).execute()
            pages = presentation.get('slides', [])
            logger.info(f"Processing '{os.path.basename(gslides_path)}' ({len(pages)} slides)...")
            
            for i, page in enumerate(pages):
                slide_num = i + 1
                page_id = page['objectId']
                video_folder = os.path.dirname(gslides_path)
                slide_folder = os.path.join(video_folder, f"Slide {slide_num}")
                
                if not os.path.exists(slide_folder):
                    logger.warning(f"Slide folder not found, creating: {slide_folder}")
                    os.makedirs(slide_folder)

                thumbnail_url = slides_service.presentations().pages().getThumbnail(
                    presentationId=pres_id, pageObjectId=page_id,
                    thumbnailProperties_thumbnailSize='LARGE'
                ).execute()['contentUrl']
                
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    output_path = os.path.join(slide_folder, f"Slide {slide_num}.png")
                    with open(output_path, 'wb') as f: f.write(response.content)
                    exported_slides += 1
                else:
                    logger.error(f"Failed to download thumbnail for slide {slide_num} from {pres_id}. Status: {response.status_code}")
                    failed_slides += 1
            
            relative_path = os.path.relpath(gslides_path, os.path.abspath(args.module_path))
            state["files"][relative_path] = mod_time
        except Exception as e:
            logger.error(f"Failed to process presentation {pres_id}: {e}")
            failed_slides += len(pages) if 'pages' in locals() else 1

    save_state(args.module_path, state)
    end_time = time.time()
    logger.info(f"Summary: {exported_slides} slides exported, {failed_slides} failed, {skipped_count} presentations skipped.")
    logger.info(f"--- Finished: Google Slides Export in {end_time - start_time:.2f} seconds ---")

def run_build(args, logger):
    """Runs the full build process: structure, tts, and optionally slides."""
    logger.info("--- Starting: Full Build Process ---")
    start_time = time.time()
    
    run_structure(args, logger)
    run_tts(args, logger)
    
    if hasattr(args, 'credentials') and args.credentials:
        run_slides(args, logger)
    else:
        logger.warning("Skipping slides step in full build: --credentials path not provided.")
        
    end_time = time.time()
    logger.info(f"--- Full Build Process Finished in {end_time - start_time:.2f} seconds ---")

# --- Main CLI Entry Point ---

def main():
    """Defines the command-line interface and executes the chosen command."""
    parser = argparse.ArgumentParser(description="Build course materials from an outline.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("module_path", type=str, help="Path to the module directory.")

    sp_structure = subparsers.add_parser("structure", help="Generate directory structure from outline.", parents=[parent_parser])
    sp_structure.set_defaults(func=run_structure)

    # --- Add --video-folder argument to commands that support targeted processing ---
    video_folder_parser = argparse.ArgumentParser(add_help=False)
    video_folder_parser.add_argument("--video-folder", type=str, help="Process only a specific video folder (e.g., 'Video 7').")
    
    sp_tts = subparsers.add_parser("tts", help="Generate audio files from text.", parents=[parent_parser, video_folder_parser])
    sp_tts.set_defaults(func=run_tts)

    sp_slides = subparsers.add_parser("slides", help="Export Google Slides to PNG.", parents=[parent_parser, video_folder_parser])
    sp_slides.add_argument("-c", "--credentials", required=True, help="Path to the service account credentials JSON file.")
    sp_slides.set_defaults(func=run_slides)

    sp_build = subparsers.add_parser("build", help="Run the full build process.", parents=[parent_parser, video_folder_parser])
    sp_build.add_argument("-c", "--credentials", help="Path to service account credentials for the optional slides step.")
    sp_build.set_defaults(func=run_build)

    args = parser.parse_args()
    
    if not os.path.isdir(args.module_path):
        print(f"Error: Module directory not found at '{args.module_path}'"); return
        
    logger = setup_logger(args.module_path, args.command)
    args.func(args, logger)

if __name__ == "__main__":
    main()
    