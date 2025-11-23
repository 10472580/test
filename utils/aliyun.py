import os
import sys
import hashlib
import time

import requests

# ========== Configuration ==========
# https://blog.csdn.net/ethnicitybeta/article/details/153734816
# os.getenv("ACCESS_TOKEN") # 阿里云token Authorization
# ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJiYThlYWU3ODNlZTU0MDRlYWJlMDVjM2NmMTAzMzhiYSIsImN1c3RvbUpzb24iOiJ7XCJjbGllbnRJZFwiOlwiMjVkelgzdmJZcWt0Vnh5WFwiLFwiZG9tYWluSWRcIjpcImJqMjlcIixcInNjb3BlXCI6W1wiRFJJVkUuQUxMXCIsXCJTSEFSRS5BTExcIixcIkZJTEUuQUxMXCIsXCJVU0VSLkFMTFwiLFwiVklFVy5BTExcIixcIlNUT1JBR0UuQUxMXCIsXCJTVE9SQUdFRklMRS5MSVNUXCIsXCJCQVRDSFwiLFwiT0FVVEguQUxMXCIsXCJJTUFHRS5BTExcIixcIklOVklURS5BTExcIixcIkFDQ09VTlQuQUxMXCIsXCJTWU5DTUFQUElORy5MSVNUXCIsXCJTWU5DTUFQUElORy5ERUxFVEVcIl0sXCJyb2xlXCI6XCJ1c2VyXCIsXCJyZWZcIjpcImh0dHBzOi8vd3d3LmFsaXBhbi5jb20vXCIsXCJkZXZpY2VfaWRcIjpcIjRiZmFiZWM5MWFlOTRmZmM4MmFlNTUyOGU0YzMxYzhiXCJ9IiwiZXhwIjoxNzYzODk2NzczLCJpYXQiOjE3NjM4ODk1MTN9.Dd3gaWKf-1Pymljav3cxS_Qh6mBzjYQwdzk9L4jB7cTfHrzylx7O27zpRrFoS_5NK4qIIKwvecfGj82PNzTX2FKHOot8Pa_35BUoSeBhDCd40r-uLw8PCiCy4m52HmDKYB2FGbFXvqdNXG60DeI7S_MfdgmeqlBv_3EGP8ZJNP4"
# if not ACCESS_TOKEN:
#     print("Error: ACCESS_TOKEN environment variable is not set.")
#     sys.exit(1)

DRIVE_ID = "2528465940"  # os.getenv("DRIVE_ID", "5808324")  # 阿里云存储id（5808324默认路径）
API_BASE = "https://api.aliyundrive.com"
UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per chunk
# ===================================


headers = {
    # "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}


def set_token(token):
    headers["Authorization"] = token


def sha1(data: bytes) -> str:
    """Calculate SHA1 hash in uppercase hex"""
    return hashlib.sha1(data).hexdigest().upper()


def post(url, data=None, json=None):
    for i in range(50):
        try:
            return requests.post(url, headers=headers, data=data, json=json, timeout=120)
        except:
            time.sleep(1)


def put(url, data):
    for i in range(50):
        try:
            return requests.put(url, data=data, headers={"Content-Type": ""}, timeout=120)
        except:
            time.sleep(1)


def get_content_hash(filepath: str) -> str:
    """Stream-calculate SHA1 for large files"""
    hash_sha1 = hashlib.sha1()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(UPLOAD_CHUNK_SIZE), b""):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest().upper()


def list_files(parent_file_id: str):
    """List files under parent ID"""
    url = f"{API_BASE}/v2/file/list"
    payload = {
        "drive_id": DRIVE_ID,
        "parent_file_id": parent_file_id
    }
    try:
        resp = post(url, json=payload)
        return resp.json()
    except Exception as e:
        print(f"Failed to list files: {e}")
        return {}


def create_folder(name: str, parent_id: str):
    """Create folder"""
    url = f"{API_BASE}/v2/file/create"
    payload = {
        "drive_id": DRIVE_ID,
        "parent_file_id": parent_id,
        "name": name,
        "type": "folder"
    }
    try:
        resp = post(url, json=payload)
        return resp.json()
    except Exception as e:
        print(f"Failed to create folder: {e}")
        return {}


def ensure_remote_dir(path: str):
    """Ensure remote directory exists, create if missing"""
    parent_id = "root"
    if not path or path.strip() == "/":
        return parent_id

    parts = [p for p in path.split('/') if p]
    for part in parts:
        items = list_files(parent_id).get("items", [])
        folder = next((x for x in items if x["name"] == part and x["type"] == "folder"), None)

        if not folder:
            print(f"Creating directory: {part}")
            res = create_folder(part, parent_id)
            if "file_id" in res:
                parent_id = res["file_id"]
            else:
                print(f"Failed to create dir: {res}")
                return None
        else:
            parent_id = folder["file_id"]

    return parent_id


def upload_single_file_chunked(local_file: str, parent_folder_id: str):
    """Upload file in chunks"""
    filename = os.path.basename(local_file)
    file_size = os.path.getsize(local_file)

    try:
        content_hash = get_content_hash(local_file)
    except Exception as e:
        print(f"Failed to read file {filename}: {e}")
        return

    print(f"Uploading: {filename} ({file_size} bytes)")
    print(f"Content Hash (SHA1): {content_hash}")

    # Step 1: Create upload session
    url = f"{API_BASE}/v2/file/create"
    num_parts = (file_size + UPLOAD_CHUNK_SIZE - 1) // UPLOAD_CHUNK_SIZE
    payload = {
        "drive_id": DRIVE_ID,
        "parent_file_id": parent_folder_id,
        "name": filename,
        "type": "file",
        "content_hash_name": "sha1",
        "content_hash": content_hash,
        "size": file_size,
        "part_info_list": [{"part_number": i + 1} for i in range(num_parts)]
    }

    try:
        resp = post(url, json=payload)
        result = resp.json()
    except Exception as e:
        print(f"Create request failed: {e}")
        return

    if "code" in result:
        if result["code"] in ["RapidProofNeed", "PreHashMatched"]:
            pass  # Ignore
        else:
            print(f"Create failed: {result}")
            return

    upload_id = result.get("upload_id")
    file_id = result.get("file_id")
    part_info_list = result.get("part_info_list", [])

    if not upload_id or not file_id or not part_info_list:
        print(f"Missing upload params: {result}")
        return

    print(f"Total chunks: {len(part_info_list)}")

    # Step 2: Upload each chunk
    uploaded_parts = []
    with open(local_file, 'rb') as f:
        for part_info in part_info_list:
            part_num = part_info["part_number"]
            start = (part_num - 1) * UPLOAD_CHUNK_SIZE
            end = min(start + UPLOAD_CHUNK_SIZE, file_size)
            chunk_size = end - start

            f.seek(start)
            chunk_data = f.read(chunk_size)

            upload_url = part_info.get("upload_url")
            if not upload_url:
                print(f"No upload URL for part {part_num}")
                return

            print(f"Uploading chunk {part_num}/{len(part_info_list)} [{start}-{end}]")

            try:
                r = put(upload_url, data=chunk_data, )
                if r.status_code != 200:
                    print(f"Chunk {part_num} failed: {r.status_code}, {r.text}")
                    return
            except Exception as e:
                print(f"Chunk {part_num} error: {e}")
                return

            uploaded_parts.append({
                "part_number": part_num,
                "etag": "*"
            })

    print("All chunks uploaded.")

    # Step 3: Complete upload
    complete_url = f"{API_BASE}/v2/file/complete"
    complete_payload = {
        "drive_id": DRIVE_ID,
        "file_id": file_id,
        "upload_id": upload_id,
        # "part_info_list": uploaded_parts
    }

    try:
        resp = post(complete_url, json=complete_payload)
        result = resp.json()
        if "file_id" in result:
            print(f"Success! File '{filename}' uploaded.")
            return True
        else:
            print(f"Complete failed: {result}")
    except Exception as e:
        print(f"Complete request failed: {e}")


def upload_aliyun(local_path, remote_path):
    if not os.path.exists(local_path):
        print(f"Local file not found: {local_path}")
        sys.exit(1)

    if not os.path.isfile(local_path):
        print("Only single file upload is supported.")
        sys.exit(1)

    target_folder_id = ensure_remote_dir(remote_path)
    if not target_folder_id:
        print("Failed to get target directory ID.")
        sys.exit(1)

    print(f"Target folder ID: {target_folder_id}")

    return upload_single_file_chunked(local_path, target_folder_id)


if __name__ == "__main__":
    upload_aliyun("../downloads/1e2f39d4448d25d0a6c5152845abebb5.zip", "韦小宝")
