# blob_storage.py
import os
from azure.storage.blob.aio import BlobServiceClient, BlobClient, ContainerClient
from fastapi import UploadFile
import uuid

from app.config import AZURE_STORAGE_CONNECTION_STRING, AZURE_BLOB_CONTAINER_NAME

# Initialize Blob Service Client asynchronously
async def get_blob_service_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# Helper to get container client
async def get_container_client() -> ContainerClient:
    blob_service_client = await get_blob_service_client()
    container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)
    try:
        await container_client.create_container()
    except Exception as e:
        # Container already exists, or other error
        print(f"Container creation failed (might already exist): {e}")
    return container_client

async def upload_file_to_blob(file: UploadFile, file_type: str = "video") -> str:
    """Uploads a file to Azure Blob Storage and returns its URL."""
    container_client = await get_container_client()
    
    # Generate a unique blob name
    file_extension = os.path.splitext(file.filename)[1]
    blob_name = f"{file_type}/{uuid.uuid4()}{file_extension}"
    
    blob_client: BlobClient = container_client.get_blob_client(blob_name)
    
    # Read file content asynchronously
    file_content = await file.read()
    
    # Upload the file
    await blob_client.upload_blob(file_content, overwrite=True)
    
    return blob_client.url

async def download_blob_chunk(blob_url: str, start_byte: int, end_byte: int) -> bytes:
    """Downloads a chunk of a blob from a given URL."""
    blob_service_client = await get_blob_service_client()
    
    # Extract container name and blob name from the URL
    # This is a simplified extraction; a robust solution might parse the URL more carefully.
    parts = blob_url.split('/')
    container_name = parts[-2]
    blob_name = parts[-1]

    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    # Download a specific range of bytes
    download_stream = await blob_client.download_blob(offset=start_byte, length=end_byte - start_byte + 1)
    chunk = await download_stream.readall()
    return chunk

async def get_blob_size(blob_url: str) -> int:
    """Gets the size of a blob from a given URL."""
    blob_service_client = await get_blob_service_client()
    parts = blob_url.split('/')
    container_name = parts[-2]
    blob_name = parts[-1]
    
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    
    props = await blob_client.get_blob_properties()
    return props.size