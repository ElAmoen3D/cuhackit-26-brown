import os
import cv2
import time
import numpy as np
from collections import Counter
from deepface import DeepFace
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
FACE_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
VERIFICATION_MODEL = "Facenet512"
MAX_WORKERS = 4
VOTE_COUNT = 10 
STRICT_THRESHOLD = 0.32    
FORGIVING_THRESHOLD = 0.45 

# Using the original Haar Cascade for speed in this version
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
REFERENCE_DATA = [] 

def precompute_db():
    print("--- Pre-computing database signatures... ---")
    if not os.path.exists(FACE_DB_DIR): return
    valid_extensions = ('.jpg', '.jpeg', '.png')
    files = [f for f in os.listdir(FACE_DB_DIR) if f.lower().endswith(valid_extensions)]
    for f in files:
        path = os.path.join(FACE_DB_DIR, f)
        try:
            results = DeepFace.represent(img_path=path, model_name=VERIFICATION_MODEL, enforce_detection=True)
            if results:
                embedding = np.array(results[0]["embedding"])
                REFERENCE_DATA.append({"name": f.split('.')[0].split('_')[0], "embedding": embedding})
        except: continue
    print(f"--- Database Ready ---\n")

class FaceTracker:
    def __init__(self):
        self.tracked_faces = {} 
        self.next_id = 0

    def get_majority(self, votes):
        if not votes: return "Scanning..."
        counts = Counter(votes)
        top_name, count = counts.most_common(1)[0]
        # Only lock in if we have a clear majority and at least 3 samples
        return top_name if len(votes) >= 3 else "Scanning..."

    def update(self, current_boxes, ai_results=None):
        new_tracking = {}
        for box in current_boxes:
            box_tuple = tuple(box)
            curr_center = np.array([box[0] + box[2]/2, box[1] + box[3]/2])
            
            best_id, min_dist = None, 80 
            for face_id, data in self.tracked_faces.items():
                prev_box = data["box"]
                prev_center = np.array([prev_box[0] + prev_box[2]/2, prev_box[1] + prev_box[3]/2])
                dist = np.linalg.norm(curr_center - prev_center)
                if dist < min_dist:
                    min_dist, best_id = dist, face_id

            if best_id is not None:
                new_tracking[best_id] = self.tracked_faces[best_id]
                new_tracking[best_id]["box"] = box_tuple
            else:
                new_tracking[self.next_id] = {
                    "box": box_tuple, 
                    "votes": [], 
                    "final_name": "Scanning...",
                    "last_scan": 0 # Track when we last ran an AI job
                }
                self.next_id += 1

        if ai_results:
            for ai_box, name in ai_results.items():
                ai_center = np.array([ai_box[0] + ai_box[2]/2, ai_box[1] + ai_box[3]/2])
                for fid, data in new_tracking.items():
                    target_center = np.array([data["box"][0] + data["box"][2]/2, data["box"][1] + data["box"][3]/2])
                    if np.linalg.norm(ai_center - target_center) < 50:
                        data["votes"].append(name)
                        if len(data["votes"]) > VOTE_COUNT: data["votes"].pop(0)
                        data["final_name"] = self.get_majority(data["votes"])

        self.tracked_faces = new_tracking
        return self.tracked_faces

def identify_face(face_crop, is_locked=False):
    try:
        live_res = DeepFace.represent(img_path=face_crop, model_name=VERIFICATION_MODEL, 
                                     enforce_detection=False, align=True, detector_backend="opencv")
        if not live_res: return "Unknown"
        live_vec = np.array(live_res[0]["embedding"])
        
        current_threshold = FORGIVING_THRESHOLD if is_locked else STRICT_THRESHOLD
        best_name, min_dist = "Unknown", current_threshold

        for ref in REFERENCE_DATA:
            cosine_dist = 1 - (np.dot(ref["embedding"], live_vec) / (np.linalg.norm(ref["embedding"]) * np.linalg.norm(live_vec)))
            if cosine_dist < min_dist:
                min_dist, best_name = cosine_dist, ref["name"]
        return best_name
    except: return "Unknown"

def main():
    precompute_db()
    cap = cv2.VideoCapture(0)
    tracker = FaceTracker()
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    pending_jobs = {} 

    while True:
        ret, frame = cap.read()
        if not ret: break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_boxes = FACE_CASCADE.detectMultiScale(gray, 1.1, 6)

        ai_updates = {}
        for future in list(pending_jobs.keys()):
            if future.done():
                ai_updates[pending_jobs.pop(future)] = future.result()

        tracked_people = tracker.update(current_boxes, ai_updates)

        # --- OPTIMIZED TRIGGER LOGIC ---
        current_time = time.time()
        for fid, data in tracked_people.items():
            box_tuple = data["box"]
            
            # 1. Check if person is already in the AI queue
            if box_tuple in pending_jobs.values(): continue
            
            # 2. Check if we have enough workers free
            if len(pending_jobs) >= MAX_WORKERS: break
            
            # 3. OFFSET STRATEGY: Only scan if not saturated OR if currently Unknown
            # If we have 10 votes and a name, we stop scanning to save resources.
            is_saturated = len(data["votes"]) >= VOTE_COUNT and data["final_name"] != "Unknown"
            
            # 4. Throttling: Don't scan the same face more than once every 0.3 seconds
            is_too_soon = (current_time - data["last_scan"]) < 0.3

            if not is_saturated and not is_too_soon:
                x, y, w, h = box_tuple
                face_crop = frame[y:y+h, x:x+w]
                if face_crop.size > 0:
                    data["last_scan"] = current_time
                    is_locked = data["final_name"] not in ["Scanning...", "Unknown"]
                    future = executor.submit(identify_face, face_crop.copy(), is_locked)
                    pending_jobs[future] = box_tuple

        # Render
        for fid, data in tracked_people.items():
            x, y, w, h = data["box"]
            name = data["final_name"]
            color = (0, 255, 0) if name not in ["Scanning...", "Unknown"] else (0, 0, 255)
            if name == "Scanning...": color = (255, 255, 0)

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            # Add saturation visual: shows [8/10] or [Locked]
            stat = "Locked" if (len(data["votes"]) >= VOTE_COUNT and name != "Unknown") else f"{len(data['votes'])}/10"
            cv2.putText(frame, f"{name} [{stat}]", (x, y-10), 2, 0.5, color, 1)

        cv2.imshow("High-Performance Vote Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    executor.shutdown()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()