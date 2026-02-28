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
import json
import threading
import numpy as np
from deepface import DeepFace
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import concurrent.futures
import time

# ── Configuration ─────────────────────────────────────────────────────────────
FACE_DB_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
VERIFICATION_MODEL = "Facenet512"
VERIFICATION_FREQ  = 10      # run AI identification every N frames
MOVE_THRESHOLD     = 120     # pixels — max distance to match a detection to a track
COSINE_THRESHOLD   = 0.40    # lower = stricter face match
JPEG_QUALITY       = 85      # video stream JPEG compression (0-100)
CAMERA_INDEX       = 0       # webcam index; try 1 or 2 if 0 doesn't work
HTTP_PORT          = 5001

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ── Shared state (guarded by state_lock) ──────────────────────────────────────
state_lock         = threading.Lock()
latest_known:      list  = []
latest_unknown:    list  = []
latest_counts:     dict  = {"known": 0, "unknown": 0, "total": 0}
latest_frame_bytes: bytes = b""
alert_log:         list  = []          # rolling list of detection events

REFERENCE_DATA: list = []             # pre-computed embeddings from face_db/
ai_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


# ── Threaded HTTP server (prevents /data blocking while /video_feed streams) ──
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ── Face database loader ──────────────────────────────────────────────────────
def precompute_db() -> None:
    print("=" * 56)
    print("  SecureView — Loading Identity Database")
    print("=" * 56)
    os.makedirs(FACE_DB_DIR, exist_ok=True)

    valid_exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    images = [f for f in os.listdir(FACE_DB_DIR) if f.lower().endswith(valid_exts)]

    if not images:
        print("  [WARN] face_db/ is empty — no identities will be recognised.")
        print(f"         Add face images to: {FACE_DB_DIR}")
    else:
        for filename in images:
            filepath = os.path.join(FACE_DB_DIR, filename)
            try:
                results = DeepFace.represent(
                    img_path      = filepath,
                    model_name    = VERIFICATION_MODEL,
                    enforce_detection = True,
                )
                if results:
                    name = os.path.splitext(filename)[0].split("_")[0].upper()
                    REFERENCE_DATA.append({
                        "name":      name,
                        "embedding": np.array(results[0]["embedding"]),
                    })
                    print(f"  [OK]   {name}  ({filename})")
            except Exception as exc:
                print(f"  [SKIP] {filename}: {exc}")

    print(f"\n  Database ready: {len(REFERENCE_DATA)} identit{'y' if len(REFERENCE_DATA)==1 else 'ies'}\n")


# ── AI face identifier ────────────────────────────────────────────────────────
def identify_face(crop: np.ndarray) -> str:
    try:
        if crop is None or crop.size == 0:
            return "UNKNOWN"

        results = DeepFace.represent(
            img_path          = crop,
            model_name        = VERIFICATION_MODEL,
            enforce_detection = False,
            align             = True,
            detector_backend  = "opencv",
        )
        if not results:
            return "UNKNOWN"

        live_vec  = np.array(results[0]["embedding"])
        norm_live = np.linalg.norm(live_vec)
        if norm_live == 0:
            return "UNKNOWN"

        best_name = "UNKNOWN"
        min_dist  = COSINE_THRESHOLD

        for ref in REFERENCE_DATA:
            norm_ref = np.linalg.norm(ref["embedding"])
            if norm_ref == 0:
                continue
            cosine_dist = 1.0 - np.dot(ref["embedding"], live_vec) / (norm_ref * norm_live)
            if cosine_dist < min_dist:
                min_dist  = cosine_dist
                best_name = ref["name"]

        return best_name

    except Exception:
        return "UNKNOWN"


# ── Proximity-based face tracker ──────────────────────────────────────────────
class FaceTracker:
    def __init__(self) -> None:
        self.tracks:   dict[int, dict] = {}
        self.next_id:  int             = 0

    def update(self, boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, dict]]:
        detections = [
            (x + w // 2, y + h // 2, x, y, w, h)
            for (x, y, w, h) in boxes
        ]

        matched:  dict[int, int] = {}
        used_det: set[int]       = set()

        for tid, td in self.tracks.items():
            best_i, best_d = None, float(MOVE_THRESHOLD)
            for i, (cx, cy, *_) in enumerate(detections):
                if i in used_det:
                    continue
                dist = np.hypot(cx - td["cx"], cy - td["cy"])
                if dist < best_d:
                    best_d, best_i = dist, i
            if best_i is not None:
                matched[tid] = best_i
                used_det.add(best_i)

        new_tracks: dict[int, dict] = {}

        for tid, idx in matched.items():
            cx, cy, x, y, w, h = detections[idx]
            new_tracks[tid] = {
                "cx": cx, "cy": cy,
                "x": x,   "y": y,
                "w": w,   "h": h,
                "name": self.tracks[tid]["name"],
            }

        for i, (cx, cy, x, y, w, h) in enumerate(detections):
            if i not in used_det:
                new_tracks[self.next_id] = {
                    "cx": cx, "cy": cy,
                    "x": x,   "y": y,
                    "w": w,   "h": h,
                    "name": "SCANNING...",
                }
                self.next_id += 1

        self.tracks = new_tracks
        return list(self.tracks.items())

    def set_name(self, orig_cx: int, orig_cy: int, name: str) -> None:
        best_tid, best_d = None, float(MOVE_THRESHOLD * 3)
        for tid, td in self.tracks.items():
            dist = np.hypot(orig_cx - td["cx"], orig_cy - td["cy"])
            if dist < best_d:
                best_d, best_tid = dist, tid
        if best_tid is not None:
            self.tracks[best_tid]["name"] = name


# ── HTTP request handler ──────────────────────────────────────────────────────
class APIHandler(BaseHTTPRequestHandler):

    def log_message(self, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/video_feed":
            self.send_response(200)
            self.send_header("Content-Type",  "multipart/x-mixed-replace; boundary=FRAME")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    with state_lock:
                        frame_bytes = latest_frame_bytes
                    if frame_bytes:
                        self.wfile.write(
                            b"--FRAME\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" +
                            frame_bytes + b"\r\n"
                        )
                    time.sleep(1 / 30)
            except (BrokenPipeError, ConnectionResetError):
                return

        elif self.path == "/data":
            with state_lock:
                payload = json.dumps({
                    "known":     latest_known,
                    "unknown":   latest_unknown,
                    "counts":    latest_counts,
                    "alerts":    alert_log[-50:],
                    "timestamp": time.time(),
                })
            self._send_json(payload)

        elif self.path == "/health":
            self._send_json(json.dumps({
                "status":     "online",
                "identities": len(REFERENCE_DATA),
                "timestamp":  time.time(),
            }))

        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control",  "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)


# ── Main video + recognition loop ─────────────────────────────────────────────
def main() -> None:
    global latest_known, latest_unknown, latest_counts, latest_frame_bytes

    precompute_db()

    server = ThreadedHTTPServer(("0.0.0.0", HTTP_PORT), APIHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"  API  →  http://localhost:{HTTP_PORT}/data")
    print(f"  Feed →  http://localhost:{HTTP_PORT}/video_feed\n")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"  ERROR: Could not open camera {CAMERA_INDEX}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    tracker:     FaceTracker = FaceTracker()
    frame_count: int         = 0
    pending_ai:  list[dict]  = []

    print("  Camera running. Press Q in the OpenCV window to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("  Camera read failed — retrying in 1 s…")
            time.sleep(1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        raw  = FACE_CASCADE.detectMultiScale(
            gray,
            scaleFactor  = 1.1,
            minNeighbors = 5,
            minSize      = (60, 60),
        )
        boxes = [tuple(b) for b in raw] if len(raw) > 0 else []

        still_pending = []
        for job in pending_ai:
            if job["future"].done():
                name = job["future"].result()
                tracker.set_name(job["cx"], job["cy"], name)
                if name not in ("UNKNOWN", "SCANNING..."):
                    alert_log.append({
                        "type": "KNOWN",
                        "name": name,
                        "time": time.strftime("%H:%M:%S"),
                    })
                else:
                    alert_log.append({
                        "type": "UNKNOWN",
                        "name": "INTRUDER",
                        "time": time.strftime("%H:%M:%S"),
                    })
                if len(alert_log) > 500:
                    alert_log.pop(0)
            else:
                still_pending.append(job)
        pending_ai = still_pending

        tracked = tracker.update(boxes)

        if frame_count % VERIFICATION_FREQ == 0 and REFERENCE_DATA:
            active_centres = {(j["cx"], j["cy"]) for j in pending_ai}
            for _, data in tracked:
                key = (data["cx"], data["cy"])
                if key not in active_centres:
                    x, y, w, h = data["x"], data["y"], data["w"], data["h"]
                    crop = frame[y: y + h, x: x + w].copy()
                    if crop.size > 0:
                        future = ai_executor.submit(identify_face, crop)
                        pending_ai.append({
                            "future": future,
                            "cx":     data["cx"],
                            "cy":     data["cy"],
                        })

        k_list: list = []
        u_list: list = []

        for _, data in tracked:
            x, y, w, h = data["x"], data["y"], data["w"], data["h"]
            cx, cy     = data["cx"], data["cy"]
            name       = data["name"]

            coords = {
                "x": int(x),  "y": int(y),
                "w": int(w),  "h": int(h),
                "center_x": int(cx),
                "center_y": int(cy),
            }

            if name == "SCANNING...":
                color, label = (0, 220, 220), "SCANNING..."
                k_list.append({"name": "SCANNING...", "coords": coords})
            elif name == "UNKNOWN":
                color, label = (0, 0, 255), "UNKNOWN"
                u_list.append(coords)
            else:
                color, label = (0, 255, 80), name
                k_list.append({"name": name, "coords": coords})

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.rectangle(frame, (x, y - th - 14), (x + tw + 10, y), color, cv2.FILLED)
            cv2.putText(frame, label, (x + 5, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
            cv2.putText(frame, f"({cx}, {cy})", (x, y + h + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        with state_lock:
            latest_known       = k_list
            latest_unknown     = u_list
            latest_counts      = {
                "known":   len([p for p in k_list if p["name"] != "SCANNING..."]),
                "unknown": len(u_list),
                "total":   len(boxes),
            }
            latest_frame_bytes = buf.tobytes()

        frame_count += 1

        # ── Local preview window ──────────────────────────────────────────
        # cv2.imshow("SecureView — Face Recognition", frame)
        # if cv2.waitKey(1) & 0xFF == ord("q"):
        #     break
        
        time.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()
    print("\n  Stopped.")

if __name__ == "__main__":
    main()