# backend_ws/app/gcs.py
from google.cloud import storage
from backend_ws.app.config import BUCKET_NAME

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def upload_to_gcs(file, gcs_path, content_type="text/csv"):
    """Uploads a file to Google Cloud Storage."""
    blob = bucket.blob(gcs_path)
    if isinstance(file, str):
        blob.upload_from_string(file, content_type=content_type)
    elif isinstance(file, bytes):
        blob.upload_from_string(file, content_type=content_type)


def load_from_gcs(gcs_path):
    """
    Downloads a file from GCS. 
    Returns bytes if local_file is None, else saves locally.
    """
    blob = bucket.blob(gcs_path)
    return blob.download_as_bytes() 


def list_gcs_files(folder_path):
    """Lists all files in GCS with the given prefix."""
    blobs = bucket.list_blobs(prefix=folder_path)
    blobslist = [blob.name for blob in blobs]
    #print(blobslist)
    return blobslist