# Local Course Structure Creator
#
# Description:
# This script runs on your local computer to automatically create a nested
# folder structure for a course. It is designed to work with local folders,
# including those synced by Google Drive for Desktop.
#
# The script is idempotent, meaning it's safe to run multiple times. If a
# folder already exists, it will simply skip it without causing an error.
#
# How to Run:
# 1. Save this file as `create_structure.py`.
# 2. Open a terminal or command prompt.
# 3. Navigate to the directory where you saved the file.
# 4. Run the script using the command: python create_structure.py
#

import os
import pathlib

def get_positive_integer_input(prompt_text):
    """A helper function to get a positive integer from the user."""
    while True:
        try:
            value = int(input(prompt_text))
            if value > 0:
                return value
            else:
                print("Please enter a number greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a whole number.")

def create_local_course_structure():
    """
    Main function to prompt the user for details and create the folder structure.
    """
    print("--- Course Structure Creation Tool ---")

    # 1. Get the root path from the user
    while True:
        root_path_str = input(r"Enter the full local path to your main course folder (e.g., G:\My Drive\My Course): ")
        root_path = pathlib.Path(root_path_str)
        if root_path.is_dir():
            break
        else:
            print("Error: The path provided does not exist or is not a directory. Please try again.")

    # 2. Get the number of modules, videos, and slides
    num_modules = get_positive_integer_input("Enter the total number of modules to create: ")
    num_videos = get_positive_integer_input("Enter the number of videos PER module: ")
    num_slides = get_positive_integer_input("Enter the number of slides PER video: ")

    print("\nStarting folder creation...\n")

    # 3. Loop and create the directory structure
    created_count = 0
    for m in range(1, num_modules + 1):
        for v in range(1, num_videos + 1):
            for s in range(1, num_slides + 1):
                # Construct the path in a platform-independent way
                # e.g., .../Module 1/Video 1/Slide 1
                relative_path = os.path.join(f"Module {m}", f"Video {v}", f"Slide {s}")
                full_path = root_path / relative_path

                # Check if the directory already exists before printing
                if not full_path.exists():
                    print(f"Creating: {full_path}")
                    created_count += 1
                
                # Create the directory.
                # `parents=True` creates any missing parent folders.
                # `exist_ok=True` prevents an error if the folder already exists.
                full_path.mkdir(parents=True, exist_ok=True)

    print("\n--- Process Complete ---")
    if created_count > 0:
        print(f"Successfully created {created_count} new slide folders.")
    else:
        print("No new folders were needed. The structure already exists.")
    print(f"The structure is ready inside: {root_path}")


# --- Main execution block ---
if __name__ == "__main__":
    create_local_course_structure()