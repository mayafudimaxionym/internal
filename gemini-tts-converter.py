import os
import sys
import wave
import google.generativeai as genai
import logging
import argparse
import time

# Configure logging
log_file = 'tts_converter.log'
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def text_to_wav_gemini(api_key, text_file_path):
    """
    Converts text from a file to a WAV audio file using the Gemini API.
    The output .wav file is saved in the same directory as the input file.

    Args:
        api_key (str): Your Google AI Studio API key.
        text_file_path (str): The full path to the input text file.
    """
    output_filename = os.path.splitext(os.path.basename(text_file_path))[0] + ".wav"
    output_path = os.path.join(os.path.dirname(text_file_path), output_filename)

    # Check if the .wav file already exists and if the .txt file has been modified
    if os.path.exists(output_path):
        txt_mtime = os.path.getmtime(text_file_path)
        wav_mtime = os.path.getmtime(output_path)
        if txt_mtime <= wav_mtime:
            logging.info(f"Skipping '{os.path.basename(text_file_path)}' as up-to-date .wav file exists.")
            return

    try:
        # --- 1. Read the text from the file ---
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text_to_speak = f.read()
            if not text_to_speak.strip():
                logging.warning(f"Skipping empty file: {text_file_path}")
                return

        logging.info(f"Processing: {os.path.basename(text_file_path)}...")

        # --- 2. Configure and Initialize the Model ---
        model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')

        # --- 3. Define the prompt with style instructions ---
        prompt = f"Read in a professional and friendly tone: {text_to_speak}"
        logging.info(f"  -> Requesting speech for: '{text_to_speak[:50]}...'")

        # --- 4. Generate the audio content with specific voice ---
        response = model.generate_content(
            contents=[prompt],
            generation_config={
                'response_modalities': ['AUDIO'],
                'speech_config': {
                    'voice_config': {
                        'prebuilt_voice_config': {
                            'voice_name': 'Puck'
                        }
                    }
                }
            }
        )

        # --- 5. Extract and save the audio data as a .wav file ---
        audio_part = response.candidates[0].content.parts[0]
        pcm_audio_data = audio_part.inline_data.data
        
        # The API returns raw signed 16-bit PCM audio at a 24kHz sample rate.
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)      # Mono
            wf.setsampwidth(2)       # 16-bit
            wf.setframerate(24000)   # 24kHz sample rate
            wf.writeframes(pcm_audio_data)

        logging.info(f"  -> Success! Audio saved to: {output_filename}")
        logging.info("Pausing for 10 seconds to avoid rate limiting...")
        time.sleep(10)


    except Exception as e:
        logging.error(f"  -> An error occurred while processing {os.path.basename(text_file_path)}: {e}")


def process_target_folder(root_directory, api_key):
    """
    Recursively walks through a directory, finds all .txt files,
    and converts them using the Gemini TTS function.
    """
    if not api_key:
        logging.error("Error: GOOGLE_API_KEY environment variable not set. Please set it before running.")
        return
        
    if not os.path.isdir(root_directory):
        logging.error(f"Error: Directory not found at '{root_directory}'")
        return

    # Configure the API key once for the entire session
    genai.configure(api_key=api_key)
    logging.info("Google AI Studio API key configured.")
    logging.info(f"Starting recursive search in: {root_directory}")
    
    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if filename.endswith(".txt"):
                full_path = os.path.join(dirpath, filename)
                text_to_wav_gemini(api_key, full_path)
    
    logging.info("Batch processing complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert .txt files to .wav using Gemini TTS.")
    parser.add_argument("folder_path", type=str, help="The full path to the folder to process.")
    args = parser.parse_args()

    # Log the initial parameters
    logging.info(f"Script started with the following parameters: folder_path='{args.folder_path}'")

    # Securely get the API key from environment variables
    my_api_key = os.getenv("GOOGLE_API_KEY")

    process_target_folder(args.folder_path.strip(), my_api_key)

    logging.shutdown()

