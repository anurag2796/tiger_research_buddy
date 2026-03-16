import cv2
import os
import glob
import math

def extract_video_frames(video_path, out_dir, num_frames=10):
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total frames detected: {total_frames}")
    
    if total_frames <= 0:
        print("Couldn't read frame count. Iterating manually...")
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret: break
            frames.append(frame)
        total_frames = len(frames)
        print(f"Actual frames loaded: {total_frames}")
        
    if total_frames == 0:
        print("No frames found!")
        return
        
    step = max(1, total_frames // num_frames)
    saved_count = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    for i in range(0, total_frames, step):
        if saved_count >= num_frames:
            break
            
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        
        if ret:
            out_path = os.path.join(out_dir, f"demo_screenshot_{saved_count+1:02d}.png")
            cv2.imwrite(out_path, frame)
            print(f"Saved: {out_path}")
            saved_count += 1
            
    cap.release()

if __name__ == "__main__":
    videos = glob.glob("/Users/anurag/.gemini/antigravity/brain/69f6b465-475e-4825-9872-5276511ae3f3/final_app_demo_*.webp")
    if videos:
        latest_video = sorted(videos)[-1]
        print(f"Extracting from: {latest_video}")
        extract_video_frames(latest_video, "docs/screenshots", 10)
    else:
        print("No video found!")
