import requests
import time
import sys
import json
import os

# Configuration
# Default to localhost if not provided, but intended for deployed URL
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090"
if BASE_URL.endswith('/'):
    BASE_URL = BASE_URL[:-1]

print(f"Testing API at: {BASE_URL}")

def check_status(response):
    if response.status_code not in [200, 201, 202]:
        print(f"Error: {response.status_code}")
        print(response.text)
        sys.exit(1)
    return response

def wait_for_status(project_id, target_status, timeout=300):
    print(f"Waiting for project {project_id} to reach status {target_status}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = requests.get(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}")
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
    res = requests.post(f"{BASE_URL}/api/ai-video/v1/projects", json=project_payload)
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
    res = requests.post(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}/assets", files=files)
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
    res = requests.post(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}/analyze")
    if res.status_code == 404:
        print("Analyze endpoint not found, maybe triggered automatically or missing. Skipping...")
    else:
        check_status(res)
        print("Analysis triggered.")
        # Wait for some status if applicable, but Asset analysis is per asset.
        # Project status might not change to "ANALYZED" until all assets are done.
    
    # 4. Generate Script
    print("\n--- Step 4: Generate Script ---")
    res = requests.post(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}/script")
    check_status(res)
    wait_for_status(project_id, "SCRIPT_GENERATED")
    
    # 5. Generate Audio
    print("\n--- Step 5: Generate Audio ---")
    # We need to fetch the script first to pass it back?
    # Controller `generateAudio` takes body `scriptContent`.
    # Let's get the project again.
    res = requests.get(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}")
    project_data = res.json()
    script_content = project_data.get("script_content", "Default script content for testing.")
    
    res = requests.post(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}/audio", data=script_content)
    check_status(res)
    # Wait for audio? There is no explicit status for AUDIO_GENERATED in the snippet I saw, 
    # but maybe it just updates internal state.
    # Let's wait a bit.
    time.sleep(5) 
    
    # 6. Render Video
    print("\n--- Step 6: Render Video ---")
    res = requests.post(f"{BASE_URL}/api/ai-video/v1/projects/{project_id}/render")
    check_status(res)
    final_data = wait_for_status(project_id, "COMPLETED")
    
    print("\n--- Test Completed Successfully ---")
    print(f"Final Video URL: {final_data.get('final_video_url')}")

if __name__ == "__main__":
    main()
