import fitz  # PyMuPDF
import os
import pytesseract
from PIL import Image
import io
import json
import uuid
import re
from tqdm import tqdm

def extract_content_from_pdf(pdf_path, output_dir="extracted_content"):
    """
    Extract text and images from a PDF file and save them in a structured way.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted content
    
    Returns:
        List of dictionaries containing extracted sections with text and images
    """
    # Create output directories if they don't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img_dir = os.path.join(output_dir, "images")
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    
    # Open the PDF
    doc = fitz.Document(pdf_path)  # Updated to fitz.Document
    
    # List to store all content
    all_content = []
    
    # For each page
    for page_num, page in enumerate(tqdm(doc, desc="Extracting pages")):
        # Extract text
        text = page.get_text()
        
        # Preprocess text to remove page numbers at beginning
        text = preprocess_page_text(text)
        
        # Extract title (usually at the beginning of the page)
        title = ""
        lines = text.split('\n')
        if lines:
            # Try to identify the title from the first few lines
            for i in range(min(5, len(lines))):  # Check first 5 lines
                candidate = lines[i].strip()
                # Skip empty lines
                if not candidate:
                    continue
                    
                # Skip if the candidate is only a number or page indicator
                if (candidate.isdigit() or 
                    re.match(r'^page\s+\d+$', candidate.lower()) or 
                    re.match(r'^\d+\s+of\s+\d+$', candidate.lower())):
                    continue
                    
                # If line is reasonably short and looks like a title
                if len(candidate) > 3 and len(candidate) < 100 and not candidate.endswith(('.', ',', ';', ':')):
                    # Additional check to ensure it's not just a page number
                    if not re.match(r'^\d+$', candidate) and not re.match(r'^page\s+\d+', candidate.lower()):
                        # Clean up the title and use it
                        title = clean_title(candidate)
                        break
                    
            # If no title found, use the first non-empty line that's not a page number
            if not title:
                for line in lines:
                    line = line.strip()
                    if line and not line.isdigit() and not re.match(r'^page\s+\d+', line.lower()):
                        title = clean_title(line)
                        break
                        
            # If still no title, use a generic placeholder
            if not title:
                title = f"Page {page_num + 1}"
        
        # Initialize page content
        page_content = {
            "id": str(uuid.uuid4()),
            "page_num": page_num + 1,
            "title": title,  # Added title field
            "text": text,
            "images": []
        }
        
        # Extract images
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Generate image filename
            image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
            image_path = os.path.join(img_dir, image_filename)
            
            # Save image
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            # Try to get image rect (position) from the page
            img_rects = []
            for img_rect in page.get_image_rects(xref):
                img_rects.append({
                    "x0": img_rect.x0,
                    "y0": img_rect.y0,
                    "x1": img_rect.x1,
                    "y1": img_rect.y1
                })
            
            # Extract text around image for context (approx 100 chars before and after)
            nearby_text = ""
            try:
                # Get the image bbox
                if img_rects:
                    # Using the first rect for simplicity
                    rect = img_rects[0]
                    # Expand the rect slightly to capture nearby text
                    expanded_rect = fitz.Rect(rect["x0"]-50, rect["y0"]-50, 
                                             rect["x1"]+50, rect["y1"]+50)
                    nearby_text = page.get_text("text", clip=expanded_rect)
                    # Replace newlines with spaces using regex for more robust handling
                    nearby_text = re.sub(r'\r?\n', ' ', nearby_text)
            except:
                pass
            
            # Try OCR on the image if it might contain text
            ocr_text = ""
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(pil_image)
                # Also clean up OCR text
                ocr_text = re.sub(r'\r?\n', ' ', ocr_text)
            except Exception as e:
                print(f"OCR error on page {page_num + 1}, image {img_index + 1}: {e}")
                pass
            
            # Add image info to page content
            page_content["images"].append({
                "filename": image_filename,
                "path": image_path,
                "position": img_rects,
                "nearby_text": nearby_text,
                "ocr_text": ocr_text
            })
        
        # Add page content to all content
        all_content.append(page_content)
    
    # Save the extracted content as JSON
    content_json_path = os.path.join(output_dir, "extracted_content.json")
    with open(content_json_path, "w", encoding="utf-8") as f:
        json.dump(all_content, f, ensure_ascii=False, indent=2)
    
    print(f"Extraction complete. Content saved to {output_dir}")
    return all_content

def identify_sections(all_content, output_dir="extracted_content"):
    """
    Try to identify document sections based on text formatting and content
    Each section is contained within a single page
    
    Args:
        all_content: List of page content dictionaries
        output_dir: Directory to save section data
    
    Returns:
        List of identified sections
    """
    # List to store all sections
    sections = []
    
    # Common section header patterns in manuals
    section_patterns = [
        r"^[A-Z][A-Z\s]{2,}$",  # ALL CAPS TITLES
        r"^[\d\.]+\s+[A-Z]",  # Numbered sections like "1.2 TITLE"
        r"^Chapter\s+\d+",  # Chapter headings
        r"^Section\s+\d+",  # Section headings
        r"^[A-Z][a-z]+\s[A-Z][a-z]+$"  # Title Case headers
    ]
    
    # Process page by page, treating each page independently
    for page in tqdm(all_content, desc="Identifying sections within pages"):
        page_num = page["page_num"]
        lines = page["text"].split("\n")
        
        # Find section headers in this page
        headers = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if this looks like a section header
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line):
                    is_header = True
                    break
                    
            # If it looks like a header and is reasonably short
            if is_header and len(line) < 100:
                headers.append((i, line))
        
        # If no headers found, use the page title as the only section
        if not headers:
            section_content = ' '.join([line.strip() for line in lines if line.strip()])
            sections.append({
                "id": str(uuid.uuid4()),
                "title": page["title"],
                "start_page": page_num,
                "content": section_content,
                "images": page["images"]
            })
        else:
            # Process each header to create sections
            for i, (header_idx, header_title) in enumerate(headers):
                # Section content starts after this header
                start_idx = header_idx + 1
                
                # Section ends at the next header or end of page
                end_idx = len(lines)
                if i < len(headers) - 1:
                    end_idx = headers[i + 1][0]
                
                # Extract section content
                section_lines = [lines[j].strip() for j in range(start_idx, end_idx) if lines[j].strip()]
                section_content = ' '.join(section_lines)
                
                # Determine which images belong to this section based on position
                # This is a simplification - assuming section header position indicates section area
                section_images = []
                header_position = start_idx / len(lines)  # Relative position of header in page
                next_header_position = end_idx / len(lines)  # Relative position of next header
                
                for img in page["images"]:
                    # If we have position information
                    if img["position"]:
                        img_y = img["position"][0]["y0"]  # Top of image
                        page_height = page.get("height", 1000)  # Default height if not available
                        img_rel_pos = img_y / page_height  # Relative position of image
                        
                        # Check if image is between this header and next
                        if img_rel_pos >= header_position and img_rel_pos < next_header_position:
                            section_images.append(img)
                    else:
                        # If no position info, use text matching
                        if img.get("nearby_text") and img["nearby_text"] in section_content:
                            section_images.append(img)
                
                # Create section
                sections.append({
                    "id": str(uuid.uuid4()),
                    "title": header_title,
                    "start_page": page_num,
                    "content": section_content,
                    "images": section_images
                })
    
    # Save sections
    sections_json_path = os.path.join(output_dir, "identified_sections.json")
    with open(sections_json_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
        
    print(f"Section identification complete. Found {len(sections)} sections within pages.")
    return sections

def chunk_sections_for_rag(sections, output_dir="extracted_content", chunk_size=500, overlap=200):
    """
    Divide sections into smaller chunks suitable for RAG
    
    Args:
        sections: List of identified sections
        output_dir: Directory to save chunks
        chunk_size: Target size of each chunk in characters
        overlap: Overlap between chunks in characters
    
    Returns:
        List of chunks with metadata
    """
    chunks = []
    
    for section in tqdm(sections, desc="Chunking sections"):
        section_text = section["content"]
        section_title = section["title"]
        
        # If section is smaller than chunk size, keep it as one chunk
        if len(section_text) <= chunk_size:
            chunks.append({
                "id": str(uuid.uuid4()),
                "section_id": section["id"],
                "section_title": section_title,
                "text": section_text,
                "start_page": section.get("start_page"),
                "chunk_index": 0,
                "images": section.get("images", [])
            })
            continue
        
        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', section_text)
        
        current_chunk = ""
        current_chunk_images = []
        chunk_index = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph exceeds chunk size, save current chunk and start new one
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "section_id": section["id"],
                    "section_title": section_title,
                    "text": current_chunk,
                    "start_page": section.get("start_page"),
                    "chunk_index": chunk_index,
                    "images": current_chunk_images
                })
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + paragraph
                
                # Associate images with chunks based on text proximity (simplified)
                current_chunk_images = []
                for img in section.get("images", []):
                    if img.get("nearby_text") and img["nearby_text"] in current_chunk:
                        current_chunk_images.append(img)
                
                chunk_index += 1
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                
                # Associate images with chunks based on text proximity
                for img in section.get("images", []):
                    if img.get("nearby_text") and img["nearby_text"] in paragraph:
                        if img not in current_chunk_images:
                            current_chunk_images.append(img)
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append({
                "id": str(uuid.uuid4()),
                "section_id": section["id"],
                "section_title": section_title,
                "text": current_chunk,
                "start_page": section.get("start_page"),
                "chunk_index": chunk_index,
                "images": current_chunk_images
            })
    
    # Process all chunks to replace newlines with spaces in text content
    print("Processing chunks to replace newlines with spaces...")
    for chunk in chunks:
        # Replace all newline characters with spaces in the text content
        chunk["text"] = re.sub(r'\n', ' ', chunk["text"])
    
    # Save chunks
    chunks_json_path = os.path.join(output_dir, "rag_chunks.json")
    with open(chunks_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        
    print(f"Chunking complete. Created {len(chunks)} chunks for RAG.")
    return chunks

def clean_title(title):
    """Clean up a title by removing common patterns like page numbers"""
    # Remove leading digits and spaces
    title = re.sub(r'^\d+\s*', '', title)
    
    # Remove common headers/footers
    patterns_to_remove = [
        r'\d+\s*$',               # Numbers at the end
        r'\bpage\s+\d+\b',        # "page X"
        r'\bchapter\s+\d+\b',     # "chapter X"
    ]
    
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    return title.strip()

def preprocess_page_text(text):
    """
    Preprocess page text to remove page numbers and repetitive information
    """
    # Remove page numbers from beginning of text
    text = re.sub(r'^\s*\d+\s*\n', '', text)
    
    # Remove common headers/footers
    lines = text.split('\n')
    cleaned_lines = []
    skip_patterns = [
        r'^\s*\d+\s*$',           # Just a page number
        r'^\s*page\s+\d+\s*$',    # Just "page X"
        r'^\s*\d+\s+of\s+\d+\s*$' # "X of Y" page indicators
    ]
    
    for line in lines:
        skip_line = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                skip_line = True
                break
        
        if not skip_line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def main(pdf_path):
    """
    Main function to process a PDF for RAG
    
    Args:
        pdf_path: Path to the PDF file
    """
    output_dir = "extracted_content_" + os.path.basename(pdf_path).replace(".pdf", "")
    
    print(f"Starting extraction process for {pdf_path}...")
    
    # Step 1: Extract content
    extracted_content = extract_content_from_pdf(pdf_path, output_dir)
    
    # Step 2: Identify sections
    sections = identify_sections(extracted_content, output_dir)
    
    # Step 3: Create chunks for RAG
    chunks = chunk_sections_for_rag(sections, output_dir)
    
    print(f"Extraction process completed successfully.")
    print(f"- Extracted {len(extracted_content)} pages")
    print(f"- Identified {len(sections)} sections")
    print(f"- Created {len(chunks)} chunks for RAG")
    print(f"All data saved to '{output_dir}' directory")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract content from a PDF manual for RAG")
    parser.add_argument("pdf_path", nargs="?", default="manual.pdf", help="Path to the PDF file (default: manual.pdf)")
    args = parser.parse_args()
    
    main(args.pdf_path)