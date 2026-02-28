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
