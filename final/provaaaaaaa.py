import os
import re
import json

def get_image_paths(image_ids):
    """
    Given a list of image IDs, return the paths of the images
    located in the extracted_content_manual/images directory.
    """
    content_dir = "extracted_content_manual"  # Define the base directory
    image_dir = os.path.join(content_dir, "images")
    image_paths = []

    if not os.path.exists(image_dir):
        print(f"Error: Image directory '{image_dir}' does not exist.")
        return []

    all_images = sorted(os.listdir(image_dir))  # Ensure images are sorted
    for i in image_ids:
        if 0 <= i < len(all_images):  # Check if index is valid
            image_paths.append(os.path.join(image_dir, all_images[i]))
    return image_paths

def get_image_paths_with_figures_from_db():
    """
    Reads the 'extracted_content.json' database and assigns figure numbers
    to images based on nearby content containing 'Fig. number'.
    """
    content_dir = "extracted_content_manual"  # Define the base directory
    db_path = os.path.join(content_dir, "extracted_content.json")

    if not os.path.exists(db_path):
        print(f"Error: JSON database '{db_path}' does not exist.")
        return {}

    # Load the JSON database
    with open(db_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    image_to_fig_map = {}

    # Iterate over database entries
    for entry in data:
        page_num = entry.get("page_num")
        images = entry.get("images", [])
        text_content = entry.get("text", "")

        for image in images:
            image_path = os.path.join(content_dir, image.get("path", ""))
            nearby_text = image.get("nearby_text", "")
            fig_number = extract_figure_number_from_text(nearby_text or text_content)

            if fig_number:
                image_to_fig_map[image_path] = {
                    "figure_number": fig_number,
                    "page_number": page_num
                }

    return image_to_fig_map

def extract_figure_number_from_text(text_content):
    """
    Extracts the figure number from the given text content.
    """
    match = re.search(r'Fig(?:ura)?\.?\s*(\d+)', text_content, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

# Example usage
image_to_fig_map = get_image_paths_with_figures_from_db()
for image, details in image_to_fig_map.items():
    print(f"Image: {image}, Figure Number: {details['figure_number']}, Page Number: {details['page_number']}")

    # Save the image-to-figure mapping to a JSON file
    output_path = os.path.join("diccionari_figures.json")
    with open(output_path, 'w', encoding='utf-8') as output_file:
        json.dump(image_to_fig_map, output_file, ensure_ascii=False, indent=4)

    print(f"Image-to-figure mapping saved to '{output_path}'.")