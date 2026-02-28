import os
import cv2
import threading
import queue
import gc
import numpy as np
import urllib.request
from collections import deque, Counter

try:
    from deepface import DeepFace
    DEEPFACE_IMPORT_ERROR = None
except Exception as import_error:
    DeepFace = None
    DEEPFACE_IMPORT_ERROR = import_error

# --- Configuration ---
FACE_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
VERIFICATION_MODEL = "Facenet512"
DISTANCE_METRIC = "euclidean_l2"
SIMILARITY_THRESHOLD = 0.68  # Optimized for Facenet512 L2
COSINE_MATCH_THRESHOLD = 0.38  # Tighter = fewer false positives
MIN_MATCH_MARGIN = 0.05        # Best match must beat 2nd-best by this much
VERIFICATION_FREQ = 10      # Re-verify more often so votes accumulate faster
VOTE_HISTORY_SIZE = 7       # Rolling window of results to vote over
MAX_WORKERS = 1  # Must be 1: TensorFlow/Keras is NOT thread-safe for concurrent inference

# --- DNN Face Detector (much more robust than Haar with hats/glasses/angles) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DNN_PROTOTXT_PATH = os.path.join(SCRIPT_DIR, "deploy.prototxt")
DNN_MODEL_PATH = os.path.join(SCRIPT_DIR, "res10_300x300_ssd_iter_140000.caffemodel")
DNN_CONFIDENCE = 0.5

def download_dnn_model():
    """Downloads the OpenCV DNN face detector model files if not already present."""
    prototxt_url = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/dnn/face_detector/deploy.prototxt"
    model_url = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"

    if not os.path.exists(DNN_PROTOTXT_PATH):
        print("Downloading DNN face detector prototxt...")
        urllib.request.urlretrieve(prototxt_url, DNN_PROTOTXT_PATH)
    if not os.path.exists(DNN_MODEL_PATH):
        print("Downloading DNN face detector model (~10MB, one-time)...")
        urllib.request.urlretrieve(model_url, DNN_MODEL_PATH)

def detect_faces_dnn(frame, net):
    """Detect faces using OpenCV's DNN SSD model. Works with hats, glasses, angles."""
    h, w = frame.shape[:2]
    # Larger blob (600x600) improves detection of small/distant faces
    blob = cv2.dnn.blobFromImage(frame, 1.0, (600, 600), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > DNN_CONFIDENCE:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2, y2 = box.astype(int)
            bw, bh = x2 - x1, y2 - y1
            if bw > 15 and bh > 15:  # Lowered from 30 to catch distant/small faces
                boxes.append((x1, y1, bw, bh))
    return boxes

def normalize_face_lighting(img):
    """Normalize lighting/saturation so embeddings are consistent across environments.
    Applies CLAHE to luminance and desaturates slightly to remove warm-light bias."""
    # Reduce saturation to remove warm/yellow color cast
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= 0.5
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    # CLAHE on luminance to flatten uneven lighting
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

# Global storage for pre-computed signatures
REFERENCE_DATA = []
MODEL_LOCK = threading.Lock()  # Serialize all TF/Keras inference calls

def open_camera():
    indices = [0, 1, 2]
    backends = [
        ("CAP_DSHOW", cv2.CAP_DSHOW),
        ("CAP_MSMF", cv2.CAP_MSMF),
        ("DEFAULT", None),
    ]

    for index in indices:
        for backend_name, backend in backends:
            if backend is None:
                cap = cv2.VideoCapture(index)
            else:
                cap = cv2.VideoCapture(index, backend)

            if cap.isOpened():
                print(f"Opened webcam: index={index}, backend={backend_name}")
                return cap

            cap.release()
    return None

def crop_with_margin(frame, box, margin_ratio=0.25):
    x, y, w, h = box
    margin_x = int(w * margin_ratio)
    margin_y = int(h * margin_ratio)

    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)
    x2 = min(frame.shape[1], x + w + margin_x)
    y2 = min(frame.shape[0], y + h + margin_y)

    return frame[y1:y2, x1:x2]

def precompute_db():
    """Calculates signatures for the database ONCE to avoid repeated Disk I/O"""
    print("--- Pre-computing database signatures... ---")
    valid_extensions = ('.jpg', '.jpeg', '.png')
    
    if not os.path.exists(FACE_DB_DIR):
        print(f"Error: Database directory not found at {FACE_DB_DIR}")
        return
        
    files = [f for f in os.listdir(FACE_DB_DIR) if f.lower().endswith(valid_extensions)]
    
    for f in files:
        path = os.path.join(FACE_DB_DIR, f)
        try:
            ref_img = cv2.imread(path)
            if ref_img is None:
                print(f"Skipping {f}: Could not read image.")
                continue
            ref_img = normalize_face_lighting(ref_img)
            results = DeepFace.represent(img_path=ref_img, model_name=VERIFICATION_MODEL, enforce_detection=True)
            if results:
                embedding = np.array(results[0]["embedding"])
                REFERENCE_DATA.append({"name": f.split('.')[0], "embedding": embedding})
                print(f"Loaded identity: {f.split('.')[0]}")
        except Exception as e:
            print(f"Skipping {f}: Could not detect face in reference image.")
    print(f"--- Database Ready: {len(REFERENCE_DATA)} identities loaded ---\n")

class FaceTracker:
    def __init__(self):
        self.tracked_faces = {} # { id: {"box", "name", "last_verified", "history"} }
        self.next_id = 0

    def update(self, current_boxes):
        new_tracking = {}

        # Build all candidate pairs (dist, box_index, face_id) within threshold
        MAX_DIST = 80
        candidates = []
        for bi, box in enumerate(current_boxes):
            curr_center = np.array([box[0] + box[2]/2, box[1] + box[3]/2])
            for face_id, data in self.tracked_faces.items():
                prev_box = data["box"]
                prev_center = np.array([prev_box[0] + prev_box[2]/2, prev_box[1] + prev_box[3]/2])
                dist = np.linalg.norm(curr_center - prev_center)
                if dist < MAX_DIST:
                    candidates.append((dist, bi, face_id))

        # Greedy one-to-one assignment: closest pairs first.
        # Each box and each tracked ID can only be matched once,
        # preventing multiple distant faces from stealing the same ID.
        candidates.sort()
        assigned_boxes = set()
        assigned_ids = set()
        for dist, bi, face_id in candidates:
            if bi in assigned_boxes or face_id in assigned_ids:
                continue
            box = current_boxes[bi]
            new_tracking[face_id] = {
                "box": tuple(box),
                "name": self.tracked_faces[face_id]["name"],
                "last_verified": self.tracked_faces[face_id].get("last_verified", 0),
                "history": self.tracked_faces[face_id].get("history", deque(maxlen=VOTE_HISTORY_SIZE)),
            }
            assigned_boxes.add(bi)
            assigned_ids.add(face_id)

        # Any unmatched boxes are new people entering the frame
        for bi, box in enumerate(current_boxes):
            if bi not in assigned_boxes:
                new_tracking[self.next_id] = {
                    "box": tuple(box),
                    "name": "Scanning...",
                    "last_verified": 0,
                    "history": deque(maxlen=VOTE_HISTORY_SIZE),
                }
                self.next_id += 1

        self.tracked_faces = new_tracking
        return self.tracked_faces

    def apply_vote(self, face_id, raw_name):
        """Add raw result to history and return the majority-voted name."""
        if face_id not in self.tracked_faces:
            return raw_name
        history = self.tracked_faces[face_id]["history"]
        history.append(raw_name)
        # Majority vote; ties broken by most-recent
        vote = Counter(history).most_common(1)[0][0]
        return vote

def identify_face(face_crop):
    try:
        if face_crop is None or face_crop.size == 0:
            return "Unknown"
        if len(face_crop.shape) != 3 or face_crop.shape[0] < 10 or face_crop.shape[1] < 10:
            return "Unknown"
        
        face_crop = normalize_face_lighting(face_crop)
        with MODEL_LOCK:
            live_res = DeepFace.represent(
                img_path=face_crop, 
                model_name=VERIFICATION_MODEL, 
                enforce_detection=False, 
                align=True,
                detector_backend="skip"
            )
        if not live_res: return "Unknown"
        
        live_vec = np.array(live_res[0]["embedding"])
        best_name = "Unknown"
        best_dist = COSINE_MATCH_THRESHOLD
        second_dist = float('inf')

        for ref in REFERENCE_DATA:
            dot_product = np.dot(ref["embedding"], live_vec)
            norm_a = np.linalg.norm(ref["embedding"])
            norm_b = np.linalg.norm(live_vec)
            cosine_dist = 1 - (dot_product / (norm_a * norm_b))

            if cosine_dist < best_dist:
                second_dist = best_dist
                best_dist = cosine_dist
                best_name = ref["name"].split('_')[0]
            elif cosine_dist < second_dist:
                second_dist = cosine_dist

        # Reject if the margin over the 2nd-best is too small (ambiguous match)
        if best_name != "Unknown" and (second_dist - best_dist) < MIN_MATCH_MARGIN:
            best_name = "Unknown"

        return best_name
    except Exception as e:
        print(f"ID Error: {e}")
        return "Unknown"

# --- Worker Thread Logic ---
def face_worker(task_queue, result_queue):
    """Long-lived daemon thread that processes faces from the queue."""
    while True:
        face_id, face_crop = task_queue.get()
        if face_crop is None: # Poison pill to exit
            break
            
        name = identify_face(face_crop)
        result_queue.put((face_id, name))
        task_queue.task_done()

def main():
    if DeepFace is None:
        print("Error: DeepFace failed to import.")
        print(f"Details: {DEEPFACE_IMPORT_ERROR}")
        print("Fix: pip install tf-keras")
        return

    if not os.path.exists(FACE_DB_DIR):
        print(f"Error: {FACE_DB_DIR} not found. Creating empty directory.")
        os.makedirs(FACE_DB_DIR)
        
    precompute_db()

    # Download & load DNN face detector
    download_dnn_model()
    face_net = cv2.dnn.readNetFromCaffe(DNN_PROTOTXT_PATH, DNN_MODEL_PATH)
    print("DNN face detector loaded (hat/glasses tolerant)")

    cap = open_camera()
    if cap is None:
        print("Error: Could not open webcam.")
        return

    tracker = FaceTracker()
    
    # Setup Queues
    task_queue = queue.Queue(maxsize=MAX_WORKERS)
    result_queue = queue.Queue()
    active_processing = set() # Track which face_ids are currently in the queue

    # Start Worker Threads
    for _ in range(MAX_WORKERS):
        t = threading.Thread(target=face_worker, args=(task_queue, result_queue), daemon=True)
        t.start()

    # Setup fullscreen window
    window_name = "CUHackit High-Speed Recognition"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. Detection (DNN-based, robust to hats/glasses/angles)
        current_boxes = detect_faces_dnn(frame, face_net)

        # 2. Update Spatial Tracker
        tracked_people = tracker.update(current_boxes)

        # 3. Process AI Results from Background Workers
        while not result_queue.empty():
            try:
                fid, raw_name = result_queue.get_nowait()
                if fid in tracked_people:
                    voted_name = tracker.apply_vote(fid, raw_name)
                    tracked_people[fid]["name"] = voted_name
                if fid in active_processing:
                    active_processing.remove(fid)
            except queue.Empty:
                break

        # 4. Trigger new AI jobs
        for face_id, data in tracked_people.items():
            if face_id in active_processing:
                continue # Already scanning this person
                
            frames_since_verify = frame_count - data.get("last_verified", 0)
            
            # If it's time to verify and our queue isn't completely full
            if frames_since_verify >= VERIFICATION_FREQ and not task_queue.full():
                box_tuple = data["box"]
                face_crop = crop_with_margin(frame, box_tuple, margin_ratio=0.25)
                
                if face_crop.size > 0:
                    try:
                        # Put copy of crop in queue, don't block main thread if full
                        task_queue.put_nowait((face_id, face_crop.copy()))
                        active_processing.add(face_id)
                        tracked_people[face_id]["last_verified"] = frame_count
                    except queue.Full:
                        pass # Queue is full, we'll catch them on the next frame

        # 5. Render
        for fid, data in tracked_people.items():
            x, y, w, h = data["box"]
            name = data["name"]
            
            if name == "Scanning...": color = (255, 255, 0) # Cyan
            elif name == "Unknown": color = (0, 0, 255)     # Red
            else: color = (0, 255, 0)                       # Green

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow(window_name, frame)
        
        # 6. Periodic Memory Cleanup
        if frame_count % 300 == 0:
            gc.collect()

        if cv2.waitKey(1) & 0xFF == ord('q'): break
        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()