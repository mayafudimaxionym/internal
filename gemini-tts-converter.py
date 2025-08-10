import os
import sys
import wave
import google.generativeai as genai

def text_to_wav_gemini(api_key, text_file_path):
    """
    Converts text from a file to a WAV audio file using the Gemini API.
    The output .wav file is saved in the same directory as the input file.

    Args:
        api_key (str): Your Google AI Studio API key.
        text_file_path (str): The full path to the input text file.
    """
    try:
        # --- 1. Read the text from the file ---
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text_to_speak = f.read()
            if not text_to_speak.strip():
                print(f"Skipping empty file: {text_file_path}")
                return

        print(f"Processing: {os.path.basename(text_file_path)}...")

        # --- 2. Configure and Initialize the Model ---
        # The API key is configured once at the start of the script
        model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')

        # --- 3. Define the prompt with style instructions from your notebook ---
        prompt = f"Read in a professional and friendly tone: {text_to_speak}"
        print(f"  -> Requesting speech for: '{text_to_speak[:50]}...'")

        # --- 4. Generate the audio content with specific voice ---
        response = model.generate_content(
            contents=[prompt],
            generation_config={
                'response_modalities': ['AUDIO'],
                'speech_config': {
                    'voice_config': {
                        'prebuilt_voice_config': {
                            'voice_name': 'Puck'  # Using the 'Puck' voice from your notebook
                        }
                    }
                }
            }
        )

        # --- 5. Extract and save the audio data as a .wav file ---
        audio_part = response.candidates[0].content.parts[0]
        pcm_audio_data = audio_part.inline_data.data
        
        # Define the output path
        output_filename = os.path.splitext(os.path.basename(text_file_path))[0] + ".wav"
        output_path = os.path.join(os.path.dirname(text_file_path), output_filename)

        # The API returns raw signed 16-bit PCM audio at a 24kHz sample rate.
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)      # Mono
            wf.setsampwidth(2)       # 16-bit
            wf.setframerate(24000)   # 24kHz sample rate
            wf.writeframes(pcm_audio_data)

        print(f"  -> Success! Audio saved to: {output_filename}")

    except Exception as e:
        print(f"  -> An error occurred while processing {os.path.basename(text_file_path)}: {e}")


def process_target_folder(root_directory, api_key):
    """
    Recursively walks through a directory, finds all .txt files,
    and converts them using the Gemini TTS function.
    """
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set. Please set it before running.")
        return
        
    if not os.path.isdir(root_directory):
        print(f"Error: Directory not found at '{root_directory}'")
        return

    # Configure the API key once for the entire session
    genai.configure(api_key=api_key)
    print("Google AI Studio API key configured.")
    print(f"Starting recursive search in: {root_directory}\n")
    
    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if filename.endswith(".txt"):
                full_path = os.path.join(dirpath, filename)
                # We no longer need to pass the API key to the conversion function
                text_to_wav_gemini(api_key, full_path)
    
    print("\nBatch processing complete.")


if __name__ == "__main__":
    # Securely get the API key from environment variables
    my_api_key = os.getenv("GOOGLE_API_KEY")

    if len(sys.argv) > 1:
        # If a path is provided as an argument, use it
        target_folder = sys.argv[1]
    else:
        # Otherwise, ask the user for the path
        target_folder = input("Please enter the full path to the folder to process and press Enter: ")
    
    process_target_folder(target_folder.strip(), my_api_key)