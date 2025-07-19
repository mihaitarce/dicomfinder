import os
import pydicom
import pandas as pd
from dicomanonymizer import anonymize_dicom_file

def is_dicom_file(file_path):
    """Check if the given file is a DICOM file."""
    # Check if the path is a file
    if not os.path.isfile(file_path):
        return False
    
    try:
        # Attempt to read the file as a DICOM dataset
        pydicom.dcmread(file_path, stop_before_pixels=True)
        return True
    except (pydicom.errors.InvalidDicomError, FileNotFoundError):
        # If an error occurs, it's not a valid DICOM file
        return False

def find_dicom_folders(root_dir):
    """Find all folders containing DICOM files within the given directory."""
    dicom_folders = set()
    
    for dirpath, _, filenames in os.walk(root_dir):
        contains_dicom = any(is_dicom_file(os.path.join(dirpath, filename)) for filename in filenames)
        if contains_dicom:
            dicom_folders.add(dirpath)
    
    return dicom_folders

# Set patient name to 'P' follwed by the sequence number
def set_patient_name_to_sequence(sequence_number):
    def set_patient_name(dataset, tag):
        element = dataset.get(tag)
        if element is not None:
            element.value = f"P{sequence_number:04}"

    return set_patient_name

# Per https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/index.html
# it is all right to retain only the year part of the birth date for
# de-identification purposes.
def set_date_to_1900(dataset, tag):
    element = dataset.get(tag)
    if element is not None:
        element.value = f"19000101"  # YYYYMMDD format

def anonymize_file(source_file_path, destination_file_path, sequence_number):
    extra_anonmymization_rules = {
        (0x0010, 0x0010): (set_patient_name_to_sequence(sequence_number)),  # Patient's Name
        (0x0010, 0x0030): (set_date_to_1900)  # Patient's Birth Date
    }

    anonymize_dicom_file(source_file_path, destination_file_path, extra_anonmymization_rules)

def copy_and_anonymize_dicom_files(dicom_folders, destination_dir):
    """Copy and anonymize DICOM files to the destination directory with sequential four-digit names."""
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    
    total_folders_processed = 0
    total_images_copied = 0
    total_size_copied = 0
    folder_mapping = []
    
    for index_folder, folder in enumerate(sorted(dicom_folders), start=1):
        print(f"Processing folder {index_folder}: {folder}")
        
        new_folder_name = f"{index_folder:04}"  # Four-digit formatting
        new_folder_path = os.path.join(destination_dir, new_folder_name)
        
        if not os.path.exists(new_folder_path):
            os.makedirs(new_folder_path)
        
        dicom_files = [f for f in os.listdir(folder) if is_dicom_file(os.path.join(folder, f))]
        
        for index_file, dicom_file in enumerate(sorted(dicom_files), start=1):
            source_file_path = os.path.join(folder, dicom_file)
            new_file_name = f"{index_file:04}.dcm"
            destination_file_path = os.path.join(new_folder_path, new_file_name)
            
            # Copy the DICOM file to the new location
            anonymize_file(source_file_path, destination_file_path, index_folder)
            
            # Get the size of the copied file
            file_size = os.path.getsize(destination_file_path)
            total_size_copied += file_size
            
            # Anonymize the copied DICOM file
            
            total_images_copied += 1

        folder_mapping.append({
            "Original": folder,
            "Anonymized": new_folder_name
        })
        
        total_folders_processed += 1
    
    return total_folders_processed, total_images_copied, total_size_copied, folder_mapping

def save_folder_mapping_to_excel(folder_mapping, excel_path):
    """Save the folder mapping to an Excel file."""
    df = pd.DataFrame(folder_mapping)
    df.to_excel(excel_path, index=False)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find, copy, and anonymize DICOM files from folders with sequential four-digit names.")
    parser.add_argument("source_dir", type=str, help="The directory to search for DICOM folders.")
    parser.add_argument("destination_dir", type=str, help="The destination directory to copy and anonymize DICOM files.")
    parser.add_argument("--list-only", action="store_true", help="List the found DICOM folders and then exit.")

    args = parser.parse_args()
    
    source_directory = args.source_dir
    destination_directory = args.destination_dir
    
    if not os.path.exists(source_directory):
        print(f"Error: The source directory '{source_directory}' does not exist.")
        parser.print_help()
        exit(1)
    
    dicom_folders = find_dicom_folders(source_directory)
    
    num_folders = len(dicom_folders)
    if num_folders == 0:
        print("\nNo DICOM files found in the specified source directory.")
    elif args.list_only:
        for folder in sorted(dicom_folders):
            print(folder)
    else:
        print(f"\nNumber of DICOM folders found: {num_folders}")
        
        total_folders_processed, total_images_copied, total_size_copied, folder_mapping = copy_and_anonymize_dicom_files(dicom_folders, destination_directory)
        
        excel_path = os.path.join(destination_directory, "folders.xlsx")
        save_folder_mapping_to_excel(folder_mapping, excel_path)

        # Convert total size to a human-readable format
        if total_size_copied < 1024:
            total_size_str = f"{total_size_copied} bytes"
        elif total_size_copied < 1024**2:
            total_size_str = f"{total_size_copied / 1024:.2f} KB"
        elif total_size_copied < 1024**3:
            total_size_str = f"{total_size_copied / (1024**2):.2f} MB"
        else:
            total_size_str = f"{total_size_copied / (1024**3):.2f} GB"
        
        print(f"\nStatistics:")
        print(f"Total DICOM folders processed: {total_folders_processed}")
        print(f"Total images copied and anonymized: {total_images_copied}")
        print(f"Total size of all datasets: {total_size_str}")