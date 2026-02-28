import os
import cv2
import threading
import queue
import numpy as np
from deepface import DeepFace
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
FACE_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
VERIFICATION_MODEL = "Facenet512"
DISTANCE_METRIC = "euclidean_l2"
SIMILARITY_THRESHOLD = 0.68  # Optimized for Facenet512 L2
VERIFICATION_FREQ = 20
MAX_WORKERS = 2

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Global storage for pre-computed signatures
REFERENCE_DATA = [] 

def precompute_db():
    """Calculates signatures for the database ONCE to avoid repeated Disk I/O"""
    print("--- Pre-computing database signatures... ---")
    valid_extensions = ('.jpg', '.jpeg', '.png')
    files = [f for f in os.listdir(FACE_DB_DIR) if f.lower().endswith(valid_extensions)]
    
    for f in files:
        path = os.path.join(FACE_DB_DIR, f)
        try:
            # Generate the embedding once
            results = DeepFace.represent(img_path=path, model_name=VERIFICATION_MODEL, enforce_detection=True)
            if results:
                embedding = np.array(results[0]["embedding"])
                REFERENCE_DATA.append({"name": f.split('.')[0], "embedding": embedding})
                print(f"Loaded identity: {f.split('.')[0]}")
        except Exception as e:
            print(f"Skipping {f}: Could not detect face in reference image.")
    print(f"--- Database Ready: {len(REFERENCE_DATA)} identities loaded ---\n")

class FaceTracker:
    def __init__(self):
        self.tracked_faces = {} # { id: {"box": tuple, "name": str} }
        self.next_id = 0

    def update(self, current_boxes, ai_results=None):
        new_tracking = {}
        for box in current_boxes:
            box_tuple = tuple(box)
            curr_center = np.array([box[0] + box[2]/2, box[1] + box[3]/2])
            
            best_id = None
            min_dist = 80 

            for face_id, data in self.tracked_faces.items():
                prev_box = data["box"]
                prev_center = np.array([prev_box[0] + prev_box[2]/2, prev_box[1] + prev_box[3]/2])
                dist = np.linalg.norm(curr_center - prev_center)
                if dist < min_dist:
                    min_dist = dist
                    best_id = face_id

            if best_id is not None:
                new_tracking[best_id] = {"box": box_tuple, "name": self.tracked_faces[best_id]["name"]}
            else:
                new_tracking[self.next_id] = {"box": box_tuple, "name": "Scanning..."}
                self.next_id += 1

        if ai_results:
            for ai_box, name in ai_results.items():
                ai_center = np.array([ai_box[0] + ai_box[2]/2, ai_box[1] + ai_box[3]/2])
                for fid, data in new_tracking.items():
                    target_center = np.array([data["box"][0] + data["box"][2]/2, data["box"][1] + data["box"][3]/2])
                    if np.linalg.norm(ai_center - target_center) < 50:
                        new_tracking[fid]["name"] = name

        self.tracked_faces = new_tracking
        return self.tracked_faces

def identify_face(face_crop):
    try:
        # Use a standardized size and ensure alignment is consistent
        live_res = DeepFace.represent(
            img_path=face_crop, 
            model_name=VERIFICATION_MODEL, 
            enforce_detection=False, 
            align=True,
            detector_backend="opencv"
        )
        if not live_res: return "Unknown"
        
        live_vec = np.array(live_res[0]["embedding"])
        best_name = "Unknown"
        
        # We'll use a slightly stricter Cosine threshold for Facenet512
        min_dist = 0.32 

        for ref in REFERENCE_DATA:
            # Cosine Distance Calculation
            dot_product = np.dot(ref["embedding"], live_vec)
            norm_a = np.linalg.norm(ref["embedding"])
            norm_b = np.linalg.norm(live_vec)
            cosine_dist = 1 - (dot_product / (norm_a * norm_b))

            if cosine_dist < min_dist:
                min_dist = cosine_dist
                # Handle names like 'john_1', 'john_2' by taking the prefix
                best_name = ref["name"].split('_')[0] 
        
        return best_name
    except Exception as e:
        print(f"ID Error: {e}")
        return "Unknown"

def main():
    if not os.path.exists(FACE_DB_DIR):
        print(f"Error: {FACE_DB_DIR} not found.")
        return
        
    precompute_db()
    cap = cv2.VideoCapture(1)
    tracker = FaceTracker()
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    pending_jobs = {} # { Future: box_tuple }
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret: break

        # Optional: resize for processing speed
        # frame = cv2.resize(frame, (640, 480))

        # 1. Detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_boxes = FACE_CASCADE.detectMultiScale(gray, 1.1, 6)

        # 2. Cleanup finished AI jobs
        ai_updates = {}
        for future in list(pending_jobs.keys()):
            if future.done():
                name = future.result()
                box_tuple = pending_jobs.pop(future)
                ai_updates[box_tuple] = name

        # 3. Update spatial tracker
        tracked_people = tracker.update(current_boxes, ai_updates)

        # 4. Trigger AI jobs if pool is ready
        if frame_count % VERIFICATION_FREQ == 0 and len(pending_jobs) < MAX_WORKERS:
            for box in current_boxes:
                box_tuple = tuple(box)
                # Only verify if this specific person isn't already being identified
                if box_tuple not in pending_jobs.values():
                    x, y, w, h = box_tuple
                    face_crop = frame[y:y+h, x:x+w]
                    if face_crop.size > 0:
                        future = executor.submit(identify_face, face_crop.copy())
                        pending_jobs[future] = box_tuple

        # 5. Render
        for fid, data in tracked_people.items():
            x, y, w, h = data["box"]
            name = data["name"]
            
            # Visual feedback
            if name == "Scanning...": color = (255, 255, 0) # Cyan
            elif name == "Unknown": color = (0, 0, 255)     # Red
            else: color = (0, 255, 0)                       # Green

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("CUHackit High-Speed Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
        frame_count += 1

    executor.shutdown()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()