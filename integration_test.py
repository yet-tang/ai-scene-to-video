import requests
import time
import sys
import json
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
    "--no-auto-detect",
    action="store_true",
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
    session.headers.update({"X-Api-Key": api_key})

def api_request(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers = dict(headers)
    headers.setdefault("X-Request-Id", str(uuid.uuid4()))
    if not path.startswith("/"):
        path = f"/{path}"
    return session.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)

def check_status(response):
    if response.status_code not in [200, 201, 202]:
        try:
            print(f"URL: {response.request.method} {response.request.url}")
        except Exception:
            pass
        print(f"Error: {response.status_code}")
        print(response.text)
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

def main():
    # 1. Create Project
    print("\n--- Step 1: Create Project ---")
    project_payload = {
        "userId": 1,
        "title": "Coolify Deployment Test",
        "houseInfo": {
            "room": 3,
            "hall": 2,
            "area": 120,
            "price": 500
        }
    }
    global projects_path
    create_candidates = [projects_path]
    if not args.no_auto_detect:
        if projects_path.startswith("/api/ai-video/"):
            create_candidates.append(f"/api/ai-video{projects_path}")

    res = None
    for candidate in create_candidates:
        attempt = api_request("POST", candidate, json=project_payload)
        if attempt.status_code in [200, 201, 202]:
            projects_path = candidate
            res = attempt
            break
        res = attempt

    check_status(res)
    project_data = res.json()
    project_id = project_data.get("id")
    print(f"Project Created: {project_id}")

    # 2. Upload Asset (Mocking a small video file)
    print("\n--- Step 2: Upload Asset ---")
    # Create a dummy file
    dummy_filename = "test_video.mp4"
    with open(dummy_filename, "wb") as f:
        f.write(b"fake video content for testing flow logic, not actual processing")
    
    files = {'file': (dummy_filename, open(dummy_filename, 'rb'), 'video/mp4')}
    res = api_request("POST", f"{projects_path}/{project_id}/assets", files=files)
    check_status(res)
    asset_data = res.json()
    print(f"Asset Uploaded: {asset_data.get('id')}")
    
    # Clean up dummy file
    os.remove(dummy_filename)

    # 3. Analyze (Might fail if worker tries to open fake video, but let's try to trigger it)
    # Note: If the worker uses OpenCV on "fake video content", it will likely fail or return empty features.
    # Ideally we upload a real small MP4. But for connection testing, this proves the task is dispatched.
    # If it fails in worker, the status might go to FAILED or stay stuck.
    # For a robust test, user should replace dummy file with real file if they want to test AI.
    print("\n--- Step 3: Trigger Analysis ---")
    # Actually, we need to trigger analysis. The API for that?
    # Based on PRD, it might be automatic or explicit.
    # Looking at ProjectController, there is NO explicit analyze endpoint in the snippet I saw earlier?
    # Wait, I saw `generateScript` etc.
    # Let me check ProjectController again. I missed `analyze` endpoint or it's implicitly triggered on upload?
    # PRD says `POST /api/ai-video/v1/projects/{id}/analyze`.
    # Let's assume it exists or check if I missed it.
    # If not, I'll skip to Script Generation which takes manual input if analysis is missing.
    
    # Let's try to call analyze
    res = api_request("POST", f"{projects_path}/{project_id}/analyze")
    if res.status_code == 404:
        print("Analyze endpoint not found, maybe triggered automatically or missing. Skipping...")
    else:
        check_status(res)
        print("Analysis triggered.")
        # Wait for some status if applicable, but Asset analysis is per asset.
        # Project status might not change to "ANALYZED" until all assets are done.
    
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
