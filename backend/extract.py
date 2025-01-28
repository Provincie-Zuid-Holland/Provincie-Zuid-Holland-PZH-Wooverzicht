import os
import zipfile
import json
from PyPDF2 import PdfReader
from docx import Document
from config import DOWNLOADS_FOLDER, EXTRACTED_FOLDER, JSON_FOLDER


def extract_zip_files(input_folder, output_folder):
    """
    Extract ZIP files containing PDFs/DOCXs and a metadata.txt file into a structured folder.

    Args:
        input_folder (str): Folder containing ZIP files.
        output_folder (str): Destination folder for extracted files.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for zip_file in os.listdir(input_folder):
        if zip_file.endswith(".zip"):
            with zipfile.ZipFile(os.path.join(input_folder, zip_file), "r") as zf:
                # Extract to a folder named after the ZIP file (minus extension)
                extract_path = os.path.join(output_folder, os.path.splitext(zip_file)[0])
                zf.extractall(extract_path)


def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file and clean it thoroughly for RAG applications.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Cleaned extracted text content with proper sentence structure.
    """
    reader = PdfReader(pdf_path)
    
    # Extract text from each page
    extracted_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    
    return clean_text(extracted_text)


def extract_text_from_docx(docx_path):
    """
    Extract text content from a DOCX file and clean it for RAG applications.
    
    Args:
        docx_path (str): Path to the DOCX file.
    
    Returns:
        str: Cleaned extracted text content with proper sentence structure.
    """
    doc = Document(docx_path)
    
    # Extract text from paragraphs and tables
    text_parts = []
    
    # Get text from paragraphs
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text.strip())
    
    # Get text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = ' '.join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text_parts.append(row_text)
    
    # Join all parts and clean
    extracted_text = '\n'.join(text_parts)
    
    return clean_text(extracted_text)


def clean_text(text):
    """
    Clean and standardize extracted text for better RAG processing.
    
    Args:
        text (str): Raw extracted text.
        
    Returns:
        str: Cleaned and standardized text.
    """
    # 1. Preserve structured data format with colon (e.g., "Date: 02.12.2024")
    preserved_lines = []
    for line in text.split('\n'):
        if ':' in line and len(line.split(':')[0].strip()) < 30:  # Preserve short key-value pairs
            preserved_lines.append(line.strip())
        else:
            preserved_lines.append(line.strip().replace('\n', ' '))
    
    # 2. Join all lines with space
    text = ' '.join(preserved_lines)
    
    # 3. Fix multiple spaces
    text = ' '.join(text.split())
    
    # 4. Ensure proper spacing after punctuation
    for punct in ['.', '!', '?']:
        text = text.replace(f"{punct} ", f"{punct} ")
        text = text.replace(f"{punct}", f"{punct} ")
    
    # 5. Fix common PDF artifacts
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" :", ":")
    
    # 6. Remove paragraph breaks for RAG
    text = text.replace(".\n", ". ")
    
    return text.strip()


def read_metadata_file(metadata_path):
    """
    Read and parse the metadata from the metadata.txt file.

    Args:
        metadata_path (str): Path to the metadata.txt file.

    Returns:
        dict: Dictionary of metadata extracted from the file.
    """
    metadata = {}
    with open(metadata_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        if ":" in line:  # Parse key-value pairs separated by a colon
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    return metadata


def combine_document_and_metadata(folder_path):
    """
    Combine document content (PDF or DOCX) and metadata into a single JSON-like structure.
    
    Args:
        folder_path (str): Path to the folder containing extracted files.
    
    Returns:
        dict: Dictionary containing combined data for the folder.
    """
    # Look for PDF and DOCX files
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    docx_files = [f for f in os.listdir(folder_path) if f.endswith(".docx")]
    metadata_file = os.path.join(folder_path, "metadata.txt")

    if not pdf_files and not docx_files:
        raise ValueError(f"No PDF or DOCX file found in folder: {folder_path}")
    if not os.path.exists(metadata_file):
        raise ValueError(f"No metadata.txt file found in folder: {folder_path}")

    # Handle either PDF or DOCX
    if pdf_files:
        doc_path = os.path.join(folder_path, pdf_files[0])
        content = extract_text_from_pdf(doc_path)
        doc_type = "pdf"
    else:
        doc_path = os.path.join(folder_path, docx_files[0])
        content = extract_text_from_docx(doc_path)
        doc_type = "docx"

    metadata = read_metadata_file(metadata_file)

    # Combine the data into a single dictionary
    combined_data = {
        "file_name": os.path.basename(doc_path),
        "file_type": doc_type,
        "content": content,
        "metadata": metadata,
    }

    return combined_data


def save_combined_data(output_folder, combined_data, file_index):
    """
    Save the combined data (document content + metadata) as a JSON file.

    Args:
        output_folder (str): Path to the folder where JSON file will be saved.
        combined_data (dict): Combined data to be saved.
        file_index (int): Unique number for the JSON file.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_path = os.path.join(output_folder, f"combined_data_{file_index}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    print(f"Saved combined data to {output_path}")


def main():
    """
    Main function to process ZIP files, extract documents and metadata, and save combined data.
    """
    extract_zip_files(DOWNLOADS_FOLDER, EXTRACTED_FOLDER)

    file_index = 1  # Start file numbering from 1
    for folder in os.listdir(EXTRACTED_FOLDER):
        folder_path = os.path.join(EXTRACTED_FOLDER, folder)
        if os.path.isdir(folder_path):
            try:
                combined_data = combine_document_and_metadata(folder_path)
                save_combined_data(JSON_FOLDER, combined_data, file_index)
                file_index += 1  # Increment the file index for unique filenames
            except ValueError as e:
                print(f"Error processing folder {folder_path}: {e}")


if __name__ == "__main__":
    main()