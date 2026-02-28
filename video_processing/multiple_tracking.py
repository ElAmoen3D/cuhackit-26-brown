"""
multiple_tracking.py — SecureView face recognition engine
==========================================================

Architecture
------------
  • OpenCV Haar cascade  → fast face *detection* every frame (lightweight)
  • DeepFace Facenet512  → AI *identification* every N frames (heavyweight, threaded)
  • FaceTracker          → stable identity assignment across frames by proximity
  • ThreadedHTTPServer   → /video_feed (MJPEG), /data (JSON), /health
  • ThreadPoolExecutor   → AI jobs run without blocking the video loop

Startup
-------
  1.  Place face images in ./face_db/  (filename = person name, e.g. alice.jpg)
  2.  python multiple_tracking.py
  3.  node server.js  (proxies this server on port 5001 → Express on 8080)
"""

import os
import cv2
import threading
import queue
import gc
import json
import time
import numpy as np
import urllib.request
from collections import deque, Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

try:
    from deepface import DeepFace
    DEEPFACE_IMPORT_ERROR = None
except Exception as import_error:
    DeepFace = None
    DEEPFACE_IMPORT_ERROR = import_error

# ── Config ─────────────────────────────────────────────────────────────────────
FACE_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
VERIFICATION_MODEL = "Facenet512"
DISTANCE_METRIC = "euclidean_l2"
SIMILARITY_THRESHOLD = 0.68  # Optimized for Facenet512 L2
COSINE_MATCH_THRESHOLD = 0.40
VERIFICATION_FREQ = 10       # Re-verify more often so votes accumulate faster
VOTE_HISTORY_SIZE = 7        # Rolling window of results to vote over
MAX_WORKERS = 1              # Must be 1: TensorFlow/Keras is NOT thread-safe for concurrent inference
HTTP_PORT = 5001

# --- DNN Face Detector ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DNN_PROTOTXT_PATH = os.path.join(SCRIPT_DIR, "deploy.prototxt")
DNN_MODEL_PATH = os.path.join(SCRIPT_DIR, "res10_300x300_ssd_iter_140000.caffemodel")
DNN_CONFIDENCE = 0.35
DNN_MIN_FACE_PX = 15
UPSCALE_FACTOR = 2.0
SMALL_FACE_UPSCALE_TARGET = 80 

# --- YuNet: full-resolution detector ---
YUNET_MODEL_PATH      = os.path.join(SCRIPT_DIR, "face_detection_yunet_2023mar.onnx")
YUNET_SCORE_THRESHOLD = 0.55  
YUNET_NMS_THRESHOLD   = 0.30

# ── Shared state (protected by lock for HTTP Server) ──────────────────────────
state_lock          = threading.Lock()
latest_known        = []
latest_unknown      = []
latest_counts       = {"known": 0, "unknown": 0, "total": 0}
latest_frame_bytes  = None
alert_log           = deque(maxlen=25)
REFERENCE_DATA      = []
MODEL_LOCK          = threading.Lock()

# ── THREADING HTTP SERVER ──────────────────────────────────────────────────────
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class APIHandler(BaseHTTPRequestHandler):

    def log_message(self, *args) -> None:
        pass

    def _send_json(self, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # ── /video_feed  (MJPEG stream) ──
        if self.path == "/video_feed":
            self.send_response(200)
            self.send_header("Content-Type",  "multipart/x-mixed-replace; boundary=FRAME")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    with state_lock:
                        fb = latest_frame_bytes
                    if fb:
                        self.wfile.write(b"--FRAME\r\nContent-Type: image/jpeg\r\n\r\n" + fb + b"\r\n")
                    time.sleep(0.033)   # ~30 fps
            except:
                return

        # ── /data  (JSON) ──
        elif self.path == "/data":
            with state_lock:
                payload = json.dumps({
                    "known":     latest_known,
                    "unknown":   latest_unknown,
                    "counts":    latest_counts,
                    "alerts":    list(alert_log),
                    "timestamp": time.time()
                })
            self._send_json(payload)

        # ── /health ──
        elif self.path == "/health":
            self._send_json(json.dumps({
                "status":     "online",
                "identities": len(REFERENCE_DATA),
                "timestamp":  time.time(),
            }))

        else:
            self.send_response(404)
            self.end_headers()

# ── Image Prep & Detection Models ──────────────────────────────────────────────
def sharpen_frame(frame):
    blurred = cv2.GaussianBlur(frame, (0, 0), 3.0)
    return cv2.addWeighted(frame, 1.5, blurred, -0.5, 0)

def normalize_face_lighting(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= 0.5
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def download_yunet_model():
    url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    if not os.path.exists(YUNET_MODEL_PATH):
        print("Downloading YuNet face detector (~370 KB, one-time)...")
        urllib.request.urlretrieve(url, YUNET_MODEL_PATH)

def load_yunet():
    try:
        download_yunet_model()
        detector = cv2.FaceDetectorYN.create(
            YUNET_MODEL_PATH, "", (640, 480),
            score_threshold=YUNET_SCORE_THRESHOLD, nms_threshold=YUNET_NMS_THRESHOLD, top_k=5000,
        )
        print("YuNet face detector loaded — full-resolution, small-face specialist")
        return detector
    except Exception as e:
        print(f"YuNet unavailable ({e}); using SSD multi-scale fallback.")
        return None

def detect_faces_yunet(frame, detector):
    h, w = frame.shape[:2]
    detector.setInputSize((w, h))
    sharp = sharpen_frame(frame)
    _, faces = detector.detect(sharp)
    boxes = []
    if faces is not None:
        for face in faces:
            x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            x, y = max(0, x), max(0, y)
            fw, fh = min(fw, w - x), min(fh, h - y)
            if fw >= DNN_MIN_FACE_PX and fh >= DNN_MIN_FACE_PX:
                boxes.append((x, y, fw, fh))
    return boxes

def download_dnn_model():
    prototxt_url = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/dnn/face_detector/deploy.prototxt"
    model_url = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
    if not os.path.exists(DNN_PROTOTXT_PATH):
        urllib.request.urlretrieve(prototxt_url, DNN_PROTOTXT_PATH)
    if not os.path.exists(DNN_MODEL_PATH):
        urllib.request.urlretrieve(model_url, DNN_MODEL_PATH)

def _run_dnn_on_frame(frame, net, scale=1.0):
    h, w = frame.shape[:2]
    if scale != 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        detect_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    else:
        detect_frame, new_w, new_h = frame, w, h

    blob = cv2.dnn.blobFromImage(detect_frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > DNN_CONFIDENCE:
            box = detections[0, 0, i, 3:7] * np.array([new_w, new_h, new_w, new_h])
            x1, y1, x2, y2 = box.astype(int)
            x1, y1, x2, y2 = int(x1 / scale), int(y1 / scale), int(x2 / scale), int(y2 / scale)
            bw, bh = x2 - x1, y2 - y1
            if bw >= DNN_MIN_FACE_PX and bh >= DNN_MIN_FACE_PX:
                boxes.append((x1, y1, bw, bh))
    return boxes

def _nms_boxes(boxes, iou_threshold=0.4):
    if not boxes: return []
    rects = np.array([[x, y, x + w, y + h] for x, y, w, h in boxes], dtype=np.float32)
    x1, y1, x2, y2 = rects[:, 0], rects[:, 1], rects[:, 2], rects[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = areas.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1, yy1 = np.maximum(x1[i], x1[order[1:]]), np.maximum(y1[i], y1[order[1:]])
        xx2, yy2 = np.minimum(x2[i], x2[order[1:]]), np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou < iou_threshold]
    return [boxes[k] for k in keep]

def detect_faces_dnn(frame, net):
    sharp = sharpen_frame(frame)
    boxes_normal  = _run_dnn_on_frame(sharp, net, scale=1.0)
    boxes_upscale = _run_dnn_on_frame(sharp, net, scale=UPSCALE_FACTOR)
    return _nms_boxes(boxes_normal + boxes_upscale)

def crop_with_margin(frame, box, margin_ratio=0.25):
    x, y, w, h = box
    margin_x, margin_y = int(w * margin_ratio), int(h * margin_ratio)
    x1, y1 = max(0, x - margin_x), max(0, y - margin_y)
    x2, y2 = min(frame.shape[1], x + w + margin_x), min(frame.shape[0], y + h + margin_y)
    return frame[y1:y2, x1:x2]

# ── DB Loader & AI Inference ───────────────────────────────────────────────────
def precompute_db():
    print("--- Pre-computing database signatures... ---")
    valid_extensions = ('.jpg', '.jpeg', '.png')
    if not os.path.exists(FACE_DB_DIR):
        os.makedirs(FACE_DB_DIR, exist_ok=True)
        return
        
    files = [f for f in os.listdir(FACE_DB_DIR) if f.lower().endswith(valid_extensions)]
    for f in files:
        path = os.path.join(FACE_DB_DIR, f)
        try:
            ref_img = cv2.imread(path)
            if ref_img is None: continue
            ref_img = normalize_face_lighting(ref_img)
            results = DeepFace.represent(img_path=ref_img, model_name=VERIFICATION_MODEL, enforce_detection=True)
            if results:
                name = f.split('.')[0].split('_')[0].upper()
                REFERENCE_DATA.append({"name": name, "embedding": np.array(results[0]["embedding"])})
                print(f"Loaded identity: {name}")
        except Exception:
            pass
    print(f"--- Database Ready: {len(REFERENCE_DATA)} identities loaded ---\n")

def upscale_small_crop(crop):
    h, w = crop.shape[:2]
    if h < SMALL_FACE_UPSCALE_TARGET or w < SMALL_FACE_UPSCALE_TARGET:
        scale = SMALL_FACE_UPSCALE_TARGET / min(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    return crop

def identify_face(face_crop):
    try:
        if face_crop is None or face_crop.size == 0: return "UNKNOWN"
        if len(face_crop.shape) != 3 or face_crop.shape[0] < 10 or face_crop.shape[1] < 10: return "UNKNOWN"
        face_crop = upscale_small_crop(face_crop) 
        face_crop = normalize_face_lighting(face_crop)
        
        with MODEL_LOCK:
            live_res = DeepFace.represent(
                img_path=face_crop, model_name=VERIFICATION_MODEL, 
                enforce_detection=False, align=True, detector_backend="skip"
            )
        if not live_res: return "UNKNOWN"
        
        live_vec = np.array(live_res[0]["embedding"])
        best_name, min_dist = "UNKNOWN", COSINE_MATCH_THRESHOLD

        for ref in REFERENCE_DATA:
            dot_product = np.dot(ref["embedding"], live_vec)
            norm_a = np.linalg.norm(ref["embedding"])
            norm_b = np.linalg.norm(live_vec)
            if norm_a == 0 or norm_b == 0: continue
            cosine_dist = 1 - (dot_product / (norm_a * norm_b))
            if cosine_dist < min_dist:
                min_dist = cosine_dist
                best_name = ref["name"]
        return best_name
    except Exception:
        return "UNKNOWN"

def face_worker(task_queue, result_queue):
    while True:
        face_id, face_crop = task_queue.get()
        if face_crop is None: break
        name = identify_face(face_crop)
        result_queue.put((face_id, name))
        task_queue.task_done()

# ── Spatial Tracker ────────────────────────────────────────────────────────────
class FaceTracker:
    def __init__(self):
        self.tracked_faces = {}
        self.next_id = 0

    def update(self, current_boxes):
        new_tracking = {}
        for box in current_boxes:
            box_tuple = tuple(box)
            curr_center = np.array([box[0] + box[2]/2, box[1] + box[3]/2])
            best_id, min_dist = None, 120 

            for face_id, data in self.tracked_faces.items():
                prev_box = data["box"]
                prev_center = np.array([prev_box[0] + prev_box[2]/2, prev_box[1] + prev_box[3]/2])
                dist = np.linalg.norm(curr_center - prev_center)
                if dist < min_dist:
                    min_dist, best_id = dist, face_id

            if best_id is not None:
                new_tracking[best_id] = {
                    "box": box_tuple, 
                    "name": self.tracked_faces[best_id]["name"],
                    "last_verified": self.tracked_faces[best_id].get("last_verified", 0),
                    "history": self.tracked_faces[best_id].get("history", deque(maxlen=VOTE_HISTORY_SIZE)),
                }
            else:
                new_tracking[self.next_id] = {
                    "box": box_tuple, "name": "SCANNING...", "last_verified": 0,
                    "history": deque(maxlen=VOTE_HISTORY_SIZE),
                }
                self.next_id += 1

        self.tracked_faces = new_tracking
        return self.tracked_faces

    def apply_vote(self, face_id, raw_name):
        if face_id not in self.tracked_faces: return raw_name
        history = self.tracked_faces[face_id]["history"]
        history.append(raw_name)
        return Counter(history).most_common(1)[0][0]

# ── Main Loop ──────────────────────────────────────────────────────────────────
def open_camera():
    for index in [0, 1, 2]:
        for backend_name, backend in [("CAP_DSHOW", cv2.CAP_DSHOW), ("CAP_MSMF", cv2.CAP_MSMF), ("DEFAULT", None)]:
            cap = cv2.VideoCapture(index, backend) if backend else cv2.VideoCapture(index)
            if cap.isOpened():
                print(f"Opened webcam: index={index}, backend={backend_name}")
                return cap
            cap.release()
    return None

def main():
    global latest_known, latest_unknown, latest_counts, latest_frame_bytes, alert_log

    if DeepFace is None:
        print(f"Error: DeepFace failed to import.\nDetails: {DEEPFACE_IMPORT_ERROR}\nFix: pip install tf-keras deepface")
        return

    precompute_db()

    # Start HTTP API
    server = ThreadedHTTPServer(("0.0.0.0", HTTP_PORT), APIHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"  API  →  http://localhost:{HTTP_PORT}/data")
    print(f"  Feed →  http://localhost:{HTTP_PORT}/video_feed\n")

    # Load face detectors
    download_dnn_model()
    face_net = cv2.dnn.readNetFromCaffe(DNN_PROTOTXT_PATH, DNN_MODEL_PATH)
    yunet_detector = load_yunet()

    cap = open_camera()
    if cap is None:
        print("Error: Could not open webcam.")
        return

    tracker = FaceTracker()
    task_queue = queue.Queue(maxsize=MAX_WORKERS)
    result_queue = queue.Queue()
    active_processing = set() 

    for _ in range(MAX_WORKERS):
        t = threading.Thread(target=face_worker, args=(task_queue, result_queue), daemon=True)
        t.start()

    frame_count = 0
    print("Camera running. Press Q in the OpenCV window to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. Detection
        if yunet_detector is not None:
            current_boxes = detect_faces_yunet(frame, yunet_detector)
        else:
            current_boxes = detect_faces_dnn(frame, face_net)

        # 2. Update Spatial Tracker
        tracked_people = tracker.update(current_boxes)

        # 3. Process AI Results
        while not result_queue.empty():
            try:
                fid, raw_name = result_queue.get_nowait()
                if fid in tracked_people:
                    old_name = tracked_people[fid]["name"]
                    voted_name = tracker.apply_vote(fid, raw_name)
                    tracked_people[fid]["name"] = voted_name
                    
                    # Generate alerts if identity shifted from Scanning to something else
                    if old_name == "SCANNING..." and voted_name != "SCANNING...":

                        if voted_name == "UNKNOWN":
                            alert_log.append({"type": "UNKNOWN", "name": "INTRUDER", "time": time.strftime("%H:%M:%S")})
                        else:
                            alert_log.append({"type": "KNOWN", "name": voted_name, "time": time.strftime("%H:%M:%S")})

                if fid in active_processing:
                    active_processing.remove(fid)
            except queue.Empty:
                break

        # 4. Trigger new AI jobs
        for face_id, data in tracked_people.items():
            if face_id in active_processing: continue 
            if (frame_count - data.get("last_verified", 0)) >= VERIFICATION_FREQ and not task_queue.full():
                face_crop = crop_with_margin(frame, data["box"], margin_ratio=0.25)
                if face_crop.size > 0:
                    try:
                        task_queue.put_nowait((face_id, face_crop.copy()))
                        active_processing.add(face_id)
                        tracked_people[face_id]["last_verified"] = frame_count
                    except queue.Full:
                        pass

        # 5. Build JSON format & UI Annotations
        k_list, u_list = [], []

        for fid, data in tracked_people.items():
            x, y, w, h = data["box"]
            cx, cy = int(x + w/2), int(y + h/2)
            name = data["name"]

            coords = {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "center_x": cx, "center_y": cy}

            if name == "SCANNING...":
                color, label = (0, 220, 220), "SCANNING..."
                k_list.append({"name": "SCANNING...", "coords": coords})
            elif name == "UNKNOWN":
                color, label = (0, 0, 255), "UNKNOWN"
                u_list.append(coords)
            else:
                color, label = (0, 255, 80), name
                k_list.append({"name": name, "coords": coords})

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.rectangle(frame, (x, y-th-14), (x+tw+10, y), color, -1)
            cv2.putText(frame, label, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,0,0), 2)
            cv2.putText(frame, f"({cx}, {cy})", (x, y+h+16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

        # 6. Update HTTP Shared State
        _, buf = cv2.imencode(".jpg", frame)
        with state_lock:
            latest_known       = k_list
            latest_unknown     = u_list
            latest_counts      = {
                "known":   len([p for p in k_list if p["name"] != "SCANNING..."]),
                "unknown": len(u_list),
                "total":   len(current_boxes)
            }
            latest_frame_bytes = buf.tobytes()

        cv2.imshow("NEXUS — Face Recognition", frame)
        
        if frame_count % 300 == 0:
            gc.collect()

        if cv2.waitKey(1) & 0xFF == ord('q'): break
        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()
    print("Stopped.")

if __name__ == "__main__":
    main()