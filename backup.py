import os
import json
import time
import zipfile
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Load JSON config
with open('backup_config.json', 'r') as f:
    config = json.load(f)

folders_to_backup = config['backup']['folders']
backup_interval = config['backup']['backup_interval_minutes'] * 60
drive_folder_id = config['backup']['google_drive_folder_id']
credentials_file = config['google_drive_api']['credentials_file']
token_file = config['google_drive_api']['token_file']

# Authenticate with Google Drive API
creds = Credentials.from_authorized_user_file(token_file)
service = build('drive', 'v3', credentials=creds)

def create_backup_zip(folder_path):
    """Creates a zip file for a given folder."""
    folder_name = os.path.basename(folder_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"{folder_name}_backup_{timestamp}.zip"
    with zipfile.ZipFile(backup_filename, 'w') as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    return backup_filename

def upload_to_google_drive(file_path):
    """Uploads a file to Google Drive."""
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [drive_folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Uploaded {file_path} to Google Drive.")
    return file

def delete_previous_backups():
    """Deletes all backups from Google Drive and permanently removes them from Trash."""
    # Get the list of files in the backup folder
    results = service.files().list(
        q=f"'{drive_folder_id}' in parents",
        fields="files(id, name, createdTime)",
        orderBy="createdTime desc"
    ).execute()

    files = results.get('files', [])
    if files:
        for file in files:
            try:
                # Delete the file from the folder (move to Trash)
                print(f"Deleting backup: {file['name']}")
                service.files().delete(fileId=file['id']).execute()
                print(f"Successfully deleted {file['name']} from the folder.")

                # Permanently delete the file from Trash
                service.files().delete(fileId=file['id']).execute()
                print(f"Successfully permanently deleted {file['name']} from Trash.")
            except Exception as e:
                print(f"Error deleting backup: {file['name']}. Error: {str(e)}")
    else:
        print("No previous backups found to delete.")

def main():
    """Main function to perform backups."""
    print("Starting folder backup service...")
    while True:
        # Delete previous backups before starting a new backup cycle
        delete_previous_backups()

        for folder_path in folders_to_backup:
            if os.path.exists(folder_path):
                print(f"Creating backup for folder: {folder_path}")
                backup_file = create_backup_zip(folder_path)
                print(f"Uploading backup for folder: {folder_path}")
                upload_to_google_drive(backup_file)
                os.remove(backup_file)  # Clean up local backup
            else:
                print(f"Warning: Folder {folder_path} does not exist. Skipping.")
        
        print(f"Backup cycle completed. Next backup in {backup_interval // 60} minutes.")
        time.sleep(backup_interval)

if config['backup']['start_on_server_launch']:
    main()
