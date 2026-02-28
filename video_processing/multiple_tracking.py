import os
import cv2
import json
import threading
import numpy as np
from deepface import DeepFace
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import concurrent.futures
import time

# ── Config ─────────────────────────────────────────────────────────────────────
FACE_DB_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
VERIFICATION_MODEL = "Facenet512"
VERIFICATION_FREQ  = 10      # AI check every N frames
MOVE_THRESHOLD     = 120     # px — max distance to consider same face
COSINE_THRESHOLD   = 0.40
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# ── Shared state (protected by lock) ──────────────────────────────────────────
state_lock          = threading.Lock()
latest_known        = []
latest_unknown      = []
latest_counts       = {"known": 0, "unknown": 0, "total": 0}
latest_frame_bytes  = None
alert_log           = []
REFERENCE_DATA      = []
ai_executor         = concurrent.futures.ThreadPoolExecutor(max_workers=4)


# ── THREADING HTTP SERVER — fixes the single-thread block bug ─────────────────
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ── Database loader ────────────────────────────────────────────────────────────
def precompute_db():
    print("=" * 50)
    print("  Loading Identity Database...")
    print("=" * 50)
    os.makedirs(FACE_DB_DIR, exist_ok=True)
    valid = ('.jpg', '.jpeg', '.png')
    for f in [fn for fn in os.listdir(FACE_DB_DIR) if fn.lower().endswith(valid)]:
        try:
            res = DeepFace.represent(
                img_path=os.path.join(FACE_DB_DIR, f),
                model_name=VERIFICATION_MODEL,
                enforce_detection=True
            )
            if res:
                name = f.split('.')[0].split('_')[0].upper()
                REFERENCE_DATA.append({"name": name, "embedding": np.array(res[0]["embedding"])})
                print(f"  [OK] Loaded: {name}")
        except Exception as e:
            print(f"  [SKIP] {f}: {e}")
    print(f"\n  Database ready: {len(REFERENCE_DATA)} identities\n")


# ── AI identifier ──────────────────────────────────────────────────────────────
def identify_face(crop):
    try:
        if crop is None or crop.size == 0:
            return "UNKNOWN"
        res = DeepFace.represent(
            img_path=crop, model_name=VERIFICATION_MODEL,
            enforce_detection=False, align=True, detector_backend="opencv"
        )
        if not res:
            return "UNKNOWN"
        live_vec  = np.array(res[0]["embedding"])
        norm_live = np.linalg.norm(live_vec)
        if norm_live == 0:
            return "UNKNOWN"
        best, min_d = "UNKNOWN", COSINE_THRESHOLD
        for ref in REFERENCE_DATA:
            nr = np.linalg.norm(ref["embedding"])
            if nr == 0:
                continue
            d = 1 - (np.dot(ref["embedding"], live_vec) / (nr * norm_live))
            if d < min_d:
                min_d, best = d, ref["name"]
        return best
    except:
        return "UNKNOWN"


# ── Proximity tracker ──────────────────────────────────────────────────────────
# Associates a stable ID with each face across frames.
# Every frame: match detections to tracks by distance → same ID follows the face.
# Name stays assigned; only position updates → coords are always live.
class FaceTracker:
    def __init__(self):
        self.tracks  = {}   # id → {cx,cy,x,y,w,h,name}
        self.next_id = 0

    def update(self, boxes):
        """boxes = [(x,y,w,h), ...]  — call every frame"""
        detections = [(x+w//2, y+h//2, x, y, w, h) for (x, y, w, h) in boxes]
        matched  = {}   # tid → det_index
        used_det = set()

        # Match existing tracks to nearest detection
        for tid, td in self.tracks.items():
            best_i, best_d = None, MOVE_THRESHOLD
            for i, (cx, cy, *_) in enumerate(detections):
                if i in used_det:
                    continue
                d = np.hypot(cx - td["cx"], cy - td["cy"])
                if d < best_d:
                    best_d, best_i = d, i
            if best_i is not None:
                matched[tid] = best_i
                used_det.add(best_i)

        # Build updated track table
        new_tracks = {}
        for tid, idx in matched.items():
            cx, cy, x, y, w, h = detections[idx]
            new_tracks[tid] = {
                "cx": cx, "cy": cy, "x": x, "y": y, "w": w, "h": h,
                "name": self.tracks[tid]["name"]   # ← keep name, update position
            }
        # New faces not matched to any existing track
        for i, (cx, cy, x, y, w, h) in enumerate(detections):
            if i not in used_det:
                new_tracks[self.next_id] = {
                    "cx": cx, "cy": cy, "x": x, "y": y, "w": w, "h": h,
                    "name": "SCANNING..."
                }
                self.next_id += 1

        self.tracks = new_tracks
        return list(self.tracks.items())   # [(tid, data), ...]

    def set_name(self, orig_cx, orig_cy, name):
        """Called when AI finishes — finds nearest current track and sets name."""
        best_tid, best_d = None, MOVE_THRESHOLD * 3
        for tid, td in self.tracks.items():
            d = np.hypot(orig_cx - td["cx"], orig_cy - td["cy"])
            if d < best_d:
                best_d, best_tid = d, tid
        if best_tid is not None:
            self.tracks[best_tid]["name"] = name


# ── HTTP API ───────────────────────────────────────────────────────────────────
class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass   # silence request logs

    def do_GET(self):
        # ── /video_feed  (MJPEG stream) ───────────────────────────────────────
        if self.path == "/video_feed":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    with state_lock:
                        fb = latest_frame_bytes
                    if fb:
                        self.wfile.write(
                            b"--FRAME\r\nContent-Type: image/jpeg\r\n\r\n" + fb + b"\r\n"
                        )
                    time.sleep(0.033)   # ~30 fps
            except:
                return

        # ── /data  (JSON) ─────────────────────────────────────────────────────
        elif self.path == "/data":
            with state_lock:
                payload = json.dumps({
                    "known":     latest_known,
                    "unknown":   latest_unknown,
                    "counts":    latest_counts,
                    "alerts":    alert_log[-25:],
                    "timestamp": time.time()
                })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(payload.encode())

        # ── /health ───────────────────────────────────────────────────────────
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "online", "identities": len(REFERENCE_DATA)}).encode())

        else:
            self.send_response(404)
            self.end_headers()


# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    global latest_known, latest_unknown, latest_counts, latest_frame_bytes

    precompute_db()

    # Start THREADED server so /data is never blocked by /video_feed
    server = ThreadedHTTPServer(("0.0.0.0", 5001), APIHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print("API running at http://localhost:5001/data")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera not found. Try VideoCapture(1)")
        return

    tracker     = FaceTracker()
    frame_count = 0
    pending_ai  = []   # [{future, cx, cy}]

    print("Camera running. Press Q in the OpenCV window to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ── Detect faces ──────────────────────────────────────────────────────
        gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        raw       = FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
        boxes     = [tuple(b) for b in raw] if len(raw) > 0 else []

        # ── Collect finished AI results ───────────────────────────────────────
        still = []
        for job in pending_ai:
            if job["future"].done():
                name = job["future"].result()
                tracker.set_name(job["cx"], job["cy"], name)
                if name not in ("UNKNOWN", "SCANNING..."):
                    alert_log.append({"type": "KNOWN",   "name": name,       "time": time.strftime("%H:%M:%S")})
                else:
                    alert_log.append({"type": "UNKNOWN", "name": "INTRUDER", "time": time.strftime("%H:%M:%S")})
            else:
                still.append(job)
        pending_ai = still

        # ── Update tracker (every frame → coords always current) ──────────────
        tracked = tracker.update(boxes)

        # ── Fire AI jobs every VERIFICATION_FREQ frames ───────────────────────
        if frame_count % VERIFICATION_FREQ == 0:
            active = {(j["cx"], j["cy"]) for j in pending_ai}
            for tid, data in tracked:
                if (data["cx"], data["cy"]) not in active:
                    x, y, w, h = data["x"], data["y"], data["w"], data["h"]
                    crop = frame[y:y+h, x:x+w].copy()
                    if crop.size > 0:
                        fut = ai_executor.submit(identify_face, crop)
                        pending_ai.append({"future": fut, "cx": data["cx"], "cy": data["cy"]})

        # ── Build JSON data + annotate frame ──────────────────────────────────
        k_list, u_list = [], []

        for tid, data in tracked:
            x, y, w, h = data["x"], data["y"], data["w"], data["h"]
            cx, cy     = data["cx"], data["cy"]
            name       = data["name"]

            # Fresh coords every frame — follows movement
            coords = {
                "x": int(x),  "y": int(y),
                "w": int(w),  "h": int(h),
                "center_x": int(cx),
                "center_y": int(cy)
            }

            if name == "SCANNING...":
                k_list.append({"name": "SCANNING...", "coords": coords})
                color, label = (0, 220, 220), "SCANNING..."
            elif name == "UNKNOWN":
                u_list.append(coords)
                color, label = (0, 0, 255), "UNKNOWN"
            else:
                k_list.append({"name": name, "coords": coords})
                color, label = (0, 255, 80), name

            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            # Label pill
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.rectangle(frame, (x, y-th-14), (x+tw+10, y), color, -1)
            cv2.putText(frame, label, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,0,0), 2)
            # Live coordinates below box
            cv2.putText(frame, f"({cx}, {cy})", (x, y+h+16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

        # ── Write shared state (read by HTTP threads) ─────────────────────────
        with state_lock:
            latest_known   = k_list
            latest_unknown = u_list
            latest_counts  = {
                "known":   len([p for p in k_list if p["name"] != "SCANNING..."]),
                "unknown": len(u_list),
                "total":   len(boxes)
            }
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            latest_frame_bytes = buf.tobytes()

        frame_count += 1
        cv2.imshow("NEXUS — Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Stopped.")


if __name__ == "__main__":
    main()