import os
import shutil

# Directory containing the images
image_dir = './Hui/cupra_frames'
full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_dir)

# Starting image number (the middle one)
start_image = 74
total_images = 93

# Verify directory exists
if not os.path.exists(full_path):
    print(f"Error: Directory '{full_path}' not found")
    exit(1)

try:
    # First phase: Add "__counter" to filenames
    print("Phase 1: Renaming files with temporary prefix...")
    counter = 1
    
    # Process all images starting from the middle
    for i in range(total_images):
        # Calculate current image number (circular from start_image)
        current_img = ((start_image - 1 + i) % total_images) + 1
        
        # Original and new filenames
        original_file = f"{current_img}.png"
        new_file = f"__{counter}_{original_file}"
        
        original_path = os.path.join(full_path, original_file)
        new_path = os.path.join(full_path, new_file)
        
        # Check if original file exists
        if os.path.exists(original_path):
            print(f"Renaming {original_file} to {new_file}")
            shutil.copy2(original_path, new_path)
            counter += 1
        else:
            print(f"Warning: File {original_file} not found")
    
    # Second phase: Remove temporary prefix and restore correct numbering
    print("\nPhase 2: Restoring final filenames...")
    for i in range(1, counter):
        temp_file = f"__{i}_*.png"
        final_file = f"{i}.png"
        
        # Find the file matching the pattern
        matching_files = [f for f in os.listdir(full_path) if f.startswith(f"__{i}_")]
        
        if matching_files:
            temp_path = os.path.join(full_path, matching_files[0])
            final_path = os.path.join(full_path, final_file)
            
            # If the final file already exists, remove it
            if os.path.exists(final_path):
                os.remove(final_path)
                
            # Rename temp file to final file
            os.rename(temp_path, final_path)
            print(f"Restored {matching_files[0]} to {final_file}")
        else:
            print(f"Warning: No file matching {temp_file} found")
    
    print("\nRenaming completed successfully!")
    print(f"Images have been reordered starting from {start_image}")

except Exception as e:
    print(f"An error occurred: {e}")
