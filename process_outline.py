# Course Outline Processor
#
# Description:
# This script reads a master outline file written in a specific Markdown
# format and breaks it down into individual .txt files for each bullet point.
# It places each file into the corresponding folder created by the
# `create_structure.py` script.
#
# How to Run:
# 1. Ensure you have created the folder structure first.
# 2. Create your master script file (e.g., `course_outline.txt`).
# 3. Save this script as `process_outline.py`.
# 4. Run from the command line: python process_outline.py
#

import os
import pathlib
import re

def process_course_outline():
    """
    Main function to parse the outline file and create individual text files.
    """
    print("--- Course Outline Processing Tool ---")

    # 1. Get the root path of the course structure
    while True:
        root_path_str = input(r"Enter the full local path to your main course folder: ")
        root_path = pathlib.Path(root_path_str)
        if root_path.is_dir():
            break
        else:
            print("Error: The path provided does not exist or is not a directory. Please try again.")

    # 2. Get the path to the master outline file
    while True:
        outline_path_str = input(r"Enter the full path to your course_outline.txt file: ")
        outline_path = pathlib.Path(outline_path_str)
        if outline_path.is_file():
            break
        else:
            print("Error: The file path provided does not exist. Please try again.")

    # 3. Initialize tracking variables
    current_module = 0
    current_video = 0
    current_slide = 0
    bullet_counter = 0
    files_created = 0

    print("\nStarting to process the outline file...\n")

    # 4. Read and process the file line by line
    with open(outline_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Detect headers using simple string matching
            if line.startswith('# '):
                # It's a Module header
                current_module = int(re.search(r'\d+', line).group())
                current_video = 0 # Reset for new module
                current_slide = 0 # Reset for new module
                print(f"Processing Module {current_module}...")

            elif line.startswith('## '):
                # It's a Video header
                current_video = int(re.search(r'\d+', line).group())
                current_slide = 0 # Reset for new video

            elif line.startswith('### '):
                # It's a Slide header
                current_slide = int(re.search(r'\d+', line).group())
                bullet_counter = 0 # Reset bullet counter for each new slide

            elif line.startswith('- '):
                # It's a bullet point
                if current_module == 0 or current_video == 0 or current_slide == 0:
                    print(f"Warning: Found a bullet point before a full Module/Video/Slide structure was defined. Skipping line: '{line}'")
                    continue
                
                bullet_counter += 1
                content = line[2:].strip() # Get text after '- '

                # Construct the path and filename
                slide_folder_path = root_path / f"Module {current_module}" / f"Video {current_video}" / f"Slide {current_slide}"
                
                # Ensure the target directory exists before writing
                if not slide_folder_path.is_dir():
                    print(f"Error: Target directory does not exist: {slide_folder_path}")
                    print("Please run the create_structure.py script first.")
                    return # Exit the function

                file_name = f"module_{current_module}_video_{current_video}_slide_{current_slide}_bullet_{bullet_counter}.txt"
                full_file_path = slide_folder_path / file_name

                # Write the content to the file
                try:
                    full_file_path.write_text(content, encoding='utf-8')
                    files_created += 1
                except Exception as e:
                    print(f"Error writing file {full_file_path}: {e}")


    print("\n--- Process Complete ---")
    print(f"Successfully created {files_created} new bullet point text files.")

# --- Main execution block ---
if __name__ == "__main__":
    process_course_outline()