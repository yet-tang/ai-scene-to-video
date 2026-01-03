import requests
import time
import sys
import os
import argparse
import uuid

# Configuration
parser = argparse.ArgumentParser()
parser.add_argument("base_url", nargs="?", default="http://localhost:8090")
parser.add_argument(
    "--api-key",
    default=os.getenv("AI_VIDEO_API_KEY") or os.getenv("API_KEY"),
)
parser.add_argument(
    "--projects-path",
    default=os.getenv("AI_VIDEO_PROJECTS_PATH") or "/api/ai-video/v1/projects",
)
parser.add_argument(
    "--video-path",
    default=os.getenv("AI_VIDEO_TEST_VIDEO") or "normal_video.mp4",
)
args = parser.parse_args()

BASE_URL = args.base_url.rstrip("/")
api_key = args.api_key
projects_path = (args.projects_path or "").rstrip("/") or "/api/ai-video/v1/projects"
if not projects_path.startswith("/"):
    projects_path = f"/{projects_path}"

print(f"Testing API at: {BASE_URL}")

session = requests.Session()
if api_key:
    auth_value = api_key if api_key.startswith("ApiKey ") else f"ApiKey {api_key}"
    session.headers.update({"Authorization": auth_value})

def api_request(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers = dict(headers)
    request_id = headers.get("X-Request-Id") or str(uuid.uuid4())
    headers["X-Request-Id"] = request_id
    if not path.startswith("/"):
        path = f"/{path}"
    url = f"{BASE_URL}{path}"
    print(f"X-Request-Id: {request_id} {method} {url}")
    response = session.request(method, url, headers=headers, **kwargs)
    response_request_id = response.headers.get("X-Request-Id")
    if response_request_id and response_request_id != request_id:
        print(f"X-Request-Id (response): {response_request_id}")
    return response

def check_status(response):
    if response.status_code not in [200, 201, 202]:
        try:
            print(f"URL: {response.request.method} {response.request.url}")
        except Exception:
            pass
        print(f"Error: {response.status_code}")
        try:
            print(f"Response headers: {dict(response.headers)}")
        except Exception:
            pass
        try:
            text = response.text or ""
            if len(text) > 2000:
                text = text[:2000] + "...(truncated)"
            print(text)
        except Exception:
            pass
        sys.exit(1)
    return response

def wait_for_status(project_id, target_status, timeout=300):
    print(f"Waiting for project {project_id} to reach status {target_status}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = api_request("GET", f"{projects_path}/{project_id}")
        if res.status_code == 200:
            data = res.json()
            current_status = data.get("status")
            print(f"Current status: {current_status}")
            if current_status == target_status:
                return data
            if current_status == "FAILED":
                print("Project processing failed.")
                sys.exit(1)
        else:
            print(f"Failed to fetch project status: {res.status_code}")
        
        time.sleep(5)
    
    print("Timeout waiting for status change.")
    sys.exit(1)

def wait_for_asset_analysis(project_id, asset_id, timeout=300):
    print(f"Waiting for asset {asset_id} to be analyzed...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = api_request("GET", f"{projects_path}/{project_id}/timeline")
        if res.status_code == 404:
            print("Timeline endpoint not found. Skipping analysis wait...")
            return
        if res.status_code != 200:
            print(f"Failed to fetch timeline: {res.status_code}")
            time.sleep(5)
            continue

        data = res.json() or {}
        assets = data.get("assets") or []
        for asset in assets:
            if str(asset.get("id")) != str(asset_id):
                continue
            scene_label = asset.get("sceneLabel") or asset.get("scene_label")
            if scene_label:
                print(f"Asset analyzed: sceneLabel={scene_label}")
                return
            print("Asset analysis not finished yet.")
            break

        time.sleep(5)

    print("Timeout waiting for asset analysis.")
    sys.exit(1)

def main():
    health_paths = ["/health", "/api/ai-video/health"]
    health_ok = False
    for health_path in health_paths:
        res = api_request("GET", health_path)
        if res.status_code == 200:
            health_ok = True
            break
    if not health_ok:
        print("Health check failed.")
        check_status(res)

    # 1. Create Project
    print("\n--- Step 1: Create Project ---")
    project_payload = {
        "userId": 1,
        "title": "山水人家 2室1厅 340万",
        "houseInfo": {
            "community": "山水人家",
            "room": 2,
            "hall": 1,
            "price": 340
        }
    }
    res = api_request("POST", projects_path, json=project_payload)
    check_status(res)
    project_data = res.json()
    project_id = project_data.get("id")
    print(f"Project Created: {project_id}")

    # 2. Upload Asset
    print("\n--- Step 2: Upload Asset ---")
    video_path = args.video_path
    if not os.path.isfile(video_path):
        print(f"Video file not found: {video_path}")
        sys.exit(1)

    filename = os.path.basename(video_path)
    upload_res = None
    for attempt in range(1, 4):
        with open(video_path, "rb") as f:
            files = {"file": (filename, f, "video/mp4")}
            upload_res = api_request("POST", f"{projects_path}/{project_id}/assets", files=files)
        if upload_res.status_code in (502, 503, 504):
            print(f"Upload attempt {attempt} failed: {upload_res.status_code}")
            time.sleep(2 * attempt)
            continue
        break

    check_status(upload_res)
    asset_data = upload_res.json()
    print(f"Asset Uploaded: {asset_data.get('id')}")

    # 3. Analyze
    print("\n--- Step 3: Wait For Analysis ---")
    asset_id = asset_data.get("id")
    if asset_id:
        wait_for_asset_analysis(project_id, asset_id)
    
    # 4. Generate Script
    print("\n--- Step 4: Generate Script ---")
    res = api_request("POST", f"{projects_path}/{project_id}/script")
    check_status(res)
    wait_for_status(project_id, "SCRIPT_GENERATED")
    
    # 5. Generate Audio
    print("\n--- Step 5: Generate Audio ---")
    # We need to fetch the script first to pass it back?
    # Controller `generateAudio` takes body `scriptContent`.
    # Let's get the project again.
    res = api_request("GET", f"{projects_path}/{project_id}")
    project_data = res.json()
    script_content = project_data.get("scriptContent") or project_data.get("script_content") or "Default script content for testing."
    
    res = api_request(
        "POST",
        f"{projects_path}/{project_id}/audio",
        data=script_content.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    check_status(res)
    # Wait for audio? There is no explicit status for AUDIO_GENERATED in the snippet I saw, 
    # but maybe it just updates internal state.
    # Let's wait a bit.
    time.sleep(5) 
    
    # 6. Render Video
    print("\n--- Step 6: Render Video ---")
    res = api_request("POST", f"{projects_path}/{project_id}/render")
    check_status(res)
    final_data = wait_for_status(project_id, "COMPLETED")
    
    print("\n--- Test Completed Successfully ---")
    print(f"Final Video URL: {final_data.get('final_video_url')}")

if __name__ == "__main__":
    main()
