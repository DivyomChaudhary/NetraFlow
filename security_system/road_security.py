import torch
torch.backends.cudnn.benchmark = True
from ultralytics import YOLO, solutions
import cv2
import numpy as np
import math
import cvzone
from sort import *
from datetime import datetime
import sqlite3
from contextlib import contextmanager
import time
import threading
import os
import io
from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.exceptions import NoCredentialsError

cap = cv2.VideoCapture('../assets/vecteezy_traffic-BStock.mp4')
wd = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
ht = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

line_pts = [(0, ht // 2 + 100), (wd, ht // 2 + 100)]
# Initialize SpeedEstimator
speed_obj = solutions.SpeedEstimator(
    model="../YOLO-weights/yolov8s.pt",
    region=line_pts,
    show=False
)

mask = cv2.imread('../assets/mask.png')
if mask is None:
    print("NO mask found!")
    exit()
mask = cv2.resize(mask, (wd,ht))

#models
coco_model = YOLO('../YOLO-weights/yolov8s.pt')
color_model = YOLO("../YOLO-weights/predict-color.pt")

#section classes
classNames = [
    "person", "bicycle", "car", "motorbike", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tvmonitor",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
    "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
    "teddy bear", "hair drier", "toothbrush"
]
colorNames = ['red', 'black', 'blue', 'car', 'green', 'grey', 'orange', 'silver', 'white', 'yellow']
#endsection

vehicles = {}
recent_alerts = []

# Tracker
tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)
limit = [100,340,1200,340]

class SecuritySystem:
    def __init__(self, blacklist_path, db_path='../logs_/traffic_security.db'):
        self.db_path = db_path
        self.db_uri = f"file:{db_path}?mode=ro"
        self.blacklist = self._load_blacklist(blacklist_path)
        self._initialize_database()
        # Pre-opening a persistent connection acts like a simple pool for this script
        self.conn = sqlite3.connect(self.db_uri, uri=True, timeout=10, check_same_thread=False)
        self.conn.execute('pragma journal_mode=wal;')
        self.bucket_name = os.getenv('BUCKET_NAME')
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
        )

    @contextmanager
    def get_cursor(self):
        """A Context Manager for safe database operations. AI assistant mentioned lower frame rates were caused by
        continuous on-off handshaking."""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    def _initialize_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS vehicle_logs
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           timestamp
                           TEXT,
                           vehicle_id
                           INTEGER,
                           type
                           TEXT,
                           color
                           TEXT,
                           speed
                           REAL,
                           is_suspicious
                           BOOLEAN,
                           s3_key
                           TEXT
                       )
                       ''')
        conn.commit()
        conn.close()

    def log_vehicle(self, v_id, v_data,s3_key):
        """Uses the context manager to log data efficiently."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_suspicious = 1 if (v_data.get("is_blacklisted", False) or v_data.get("hazard_type") is not None) else 0
        speed = v_data.get("max_speed", 0)

        # This block replaces opening/closing connections manually
        with self.get_cursor() as cursor:
            cursor.execute('''
                           INSERT INTO vehicle_logs (timestamp, vehicle_id, type, color,speed, is_suspicious, s3_key)
                           VALUES (?, ?, ?, ?, ?, ?, ?)
                           ''', (timestamp, v_id, v_data['type'], v_data['color'],speed, is_suspicious, s3_key))

    def wipe_system(self, password_provided):
        """Securely deletes all database logs and S3 images."""
        # Check against environment variable
        if password_provided != os.getenv('ADMIN_PASSWORD'):
            return False, "Invalid Password"

        try:
            # 1. Clear Database
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM vehicle_logs where id >= 0")

            # 2. Clear S3 Bucket
            # List all files and delete them
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
            return True, "System wiped successfully."
        except Exception as e:
            return False, str(e)

    def _load_blacklist(self, path):
        """Loads the watch list into a set for O(1) lookup speed."""
        watchlist = set()
        try:
            with open(path, mode='r') as f:
                import csv
                reader = csv.DictReader(f)
                for row in reader:
                    watchlist.add((row['Type'].strip().lower(), row['Color'].strip().lower()))
        except FileNotFoundError:
            print(f"Warning: {path} not found. Blacklist is empty.")
        return watchlist

    def generate_vehicle_signature(self, speed=0):
        speed_code = speed if speed != "Scanning..." else "UNK"
        return f"{int(speed)} km/h"

    def check_status(self, vehicle_type, color, is_exception):
        """Business logic to determine if a vehicle is suspicious."""
        # Suspicious if color is 'speeding/hidden' OR matches the blacklist
        is_suspicious = is_exception or (vehicle_type.lower(), color.lower()) in self.blacklist
        return is_suspicious

    def upload_evidence_direct(self, crop_img, file_name):
        """Uploads image directly from RAM to S3 with descriptive naming."""
        try:

            # Convert OpenCV image (NumPy array) to JPEG in memory, took AI assistance
            _, buffer = cv2.imencode('.jpg', crop_img)
            io_buf = io.BytesIO(buffer)
            # print(f"DEBUG: Attempting upload for {file_name} to {self.bucket_name}")

            self.s3_client.upload_fileobj(
                io_buf,
                self.bucket_name,
                file_name,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
            print(f"✅ SUCCESS: {file_name} is now in S3")
            return True
        except Exception as e:
            print(f"❌ S3 UPLOAD CRASHED: {str(e)}")
            return None

    def analyze_behavior(self, v_id, v_data, current_frame_time, all_vehicles):  # Added self and all_vehicles
        traj = v_data["trajectory"]
        if len(traj) < 2: return

        # 1. Limit Trajectory Length (Prevent memory leak)
        if len(traj) > 20:
            v_data["trajectory"] = traj[-20:]

        # 2. Velocity Calculation
        dx = traj[-1][0] - traj[-2][0]
        dy = traj[-1][1] - traj[-2][1]
        velocity = math.sqrt(dx ** 2 + dy ** 2)

        # 3. Stalling Logic
        if velocity < 1.0:
            if "stall_start" not in v_data:
                v_data["stall_start"] = current_frame_time
            elif current_frame_time - v_data["stall_start"] > 3.0:
                v_data["hazard_type"] = "STALLED"
        else:
            v_data["stall_start"] = current_frame_time

        # 4. Tailgating Logic
        if velocity > 15:
            for other_id, other_data in all_vehicles.items():
                if other_id != v_id and len(other_data["trajectory"]) > 0:
                    dist = math.dist(traj[-1], other_data["trajectory"][-1])
                    if dist < 60:  # Threshold
                        v_data["hazard_type"] = "TAILGATING"

security = SecuritySystem(blacklist_path='../logs_/blacklist.csv')

def update_security_dashboard(v_id, v_type, v_color):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"{timestamp} - ID {v_id}: {v_color} {v_type}"
    recent_alerts.insert(0, entry)  # Add to start of list
    # Keep only the last 5 events
    if len(recent_alerts) > 5: recent_alerts.pop()


def process_frame(image, imgRegion):
    # This automatically tracks objects and calculates their speed
    speed_res = speed_obj(image)
    image = speed_res.plot_im
    results = coco_model(imgRegion, stream=True, imgsz=480, verbose=False)
    detections = np.empty((0, 5))

    max_speed_tracker = {}
    temp_classes = {}

    for r in results:
        boxes = r.boxes
        for box in boxes:
            # bounding box
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            conf_1 = math.ceil((box.conf[0] * 100)) / 100
            origin = (max(0, x1), max(28, y1 - 10))  # handle overflow

            # class name
            cls = int(box.cls[0])
            current_class = classNames[cls]
            if current_class in ["car", "truck", "bus", "motorbike"] and conf_1 > 0.6:
                current_array = np.array([x1, y1, x2, y2, conf_1])
                detections = np.vstack((detections, current_array))
                temp_classes[(x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2)] = current_class

            # else:
            #     cv2.rectangle(image,(x1,y1),(x2,y2),(0,0,255),1) # toggle on for classifying non-car detections with red color

    tracker_results = tracker.update(detections)
    # cv2.line(image,(limit[0], limit[1]),(limit[2], limit[3]),(0,255,255),4)

    for result in tracker_results:
        x1, y1, x2, y2, Id = map(int, result)
        w, h = x2 - x1, y2 - y1
        # toggle this on to check if id are stateful or stateless
        # cv2.putText(image, f'{Id}', (max(0,x1), max(28,y1)), thickness=2, fontScale=1.5, fontFace=cv2.FONT_HERSHEY_SIMPLEX, color=(255,255,255))

        # tracker points
        cx, cy = x1 + (w // 2), y1 + (h // 2)
        # cv2.circle(image,(cx,cy),5,(0,0,255),-1) # can toggle on for tracker points visibility

        if Id not in vehicles:
            v_type = "Vehicle"
            for pos, name in temp_classes.items():
                if abs(pos[0] - cx) < 20 and abs(pos[1] - cy) < 20:
                    v_type = name
            vehicles[Id] = {
                            "type": v_type,
                            "color": "Scanning...",
                            "logged": False,
                            "trajectory": [],  # Store the last 10 (x,y) positions
                            "speed": 0,
                            "max_speed": 0,
                            "is_aggressive": False,
                            "uploaded": False
                            }

        v_data = vehicles[Id]
        v_data["trajectory"].append((cx,cy))
        current_speed = speed_obj.spd.get(Id, 0)
        v_data["speed"] = current_speed
        if current_speed > v_data["max_speed"]:
            v_data["max_speed"] = current_speed

        # Speed threshold hazard (New behavior check)
        if v_data["speed"] > 100:  # Example limit 100km/h
            v_data["hazard_type"] = "SPEEDING"

        if limit[0] < cx < limit[2] and limit[1] - 15 < cy < limit[3] + 15:
            if not vehicles[Id]["logged"]:
                crop_img = image[max(0, y1 - 20):min(ht, y2 + 20), max(0, x1 - 20):min(wd, x2 + 20)]
                if crop_img.size != 0:
                    color_results = color_model(crop_img)

                    if len(color_results[0].boxes) > 0:
                        detected_color = colorNames[int(color_results[0].boxes.cls[0])]
                        is_exception = False
                    else:
                        detected_color = "speeding/hidden"
                        is_exception = True

                    vehicles[Id]["logged"] = True
                    vehicles[Id]["color"] = detected_color

                    is_suspicious = security.check_status(vehicles[Id]["type"], detected_color, is_exception)
                    vehicles[Id]["is_blacklisted"] = is_suspicious

                    # s3 object name
                    file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    s3_filename = f"{detected_color}_{vehicles[Id]['type']}_{Id}_{file_timestamp}.jpg"

                    if is_suspicious and not vehicles[Id]["uploaded"]:
                        vehicles[Id]["uploaded"] = True
                        t = (threading.Thread(
                            target=security.upload_evidence_direct,
                            args=(crop_img.copy(), s3_filename)
                        ))
                        t.daemon = True
                        t.start()
                        alert_msg = f"ALERT!! : {detected_color} {vehicles[Id]['type']} (ID:{Id})"
                        if alert_msg not in recent_alerts:
                            recent_alerts.insert(0, alert_msg)
                    else:
                        update_security_dashboard(Id, vehicles[Id]["type"], vehicles[Id]["color"])

                    security.log_vehicle(Id, vehicles[Id], s3_filename)
            # cv2.line(image, (limit[0], limit[1]), (limit[2], limit[3]), (0, 255, 0), 4) # can toggle it on for limit setting
            signature = security.generate_vehicle_signature(v_data["speed"])

            # Abstraction Label (Signature)
            cv2.rectangle(image, (x1, y1 - 22), (x1 + 160, y1), (40, 40, 40), -1)
            cv2.putText(image, signature, (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            if v_data.get("is_aggressive"):
                cvzone.putTextRect(image, "SWERVING", (x1, y2 + 25), scale=1, thickness=1, colorR=(0, 0, 255), offset=3)

        recent_points = v_data["trajectory"][-10:]
        if len(v_data["trajectory"]) >= 10:
            total_hori_drift = abs(recent_points[-1][0] - recent_points[0][0])

            if total_hori_drift > 100:
                v_data["is_aggressive"] = True

        display_text = f"ID:{Id} {v_data['type']} | {v_data['color']}"
        # State 1: Logged and Blacklisted (Suspicious)
        if v_data.get("is_blacklisted", False):
            b_color = (0, 0, 255)
            thickness = 3

        # State 2: Logged but Safe (Normal)
        elif v_data.get("logged", False):
            b_color = (0, 255, 0)
            thickness = 2

        # State 3: Unlogged (Scanning/Initial Detection)
        else:
            b_color = (255, 0, 255)
            thickness = 2

        # cv2.rectangle(image, (x1, y1), (x2, y2), b_color, thickness)
        # cvzone.putTextRect(image, display_text , (max(0, x1), max(35, y1)),
        #                    scale=1, thickness=1, offset=3, colorR=b_color)

        if v_data.get("is_blacklisted") or "hazard_type" in v_data:
            color = (0, 0, 255)
            thickness = 3
            points = v_data["trajectory"]

            if "hazard_type" in v_data:
                color = (0, 0, 255)
                thickness = 2
                cvzone.putTextRect(image, v_data["hazard_type"], (x1, y2 + 20), scale=1, colorR=color)

            # Draw the 'Ghost' movement tail
            for inc in range(1, len(points)):
                cv2.line(image, points[inc - 1], points[inc], color, thickness)

        security.analyze_behavior(Id, vehicles[Id], time.time(), vehicles)

prev_time = 0

while True:
    ret, image = cap.read()
    if not ret: break
    if mask is None:
        print("Mask exception")
        exit()

    imgRegion = cv2.bitwise_and(image, mask)
    process_frame(image, imgRegion)
    curr_time = time.time()

    # UI Dashboard
    fps = 1 + 1 / (curr_time - prev_time)
    prev_time = curr_time

    # UI Panel
    cv2.rectangle(image, (wd - 200, 0), (wd, 100), (0, 0, 0), -1)
    cv2.putText(image, f"SQL: Connected", (wd - 180, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(image, "NETRAFLOW SEC-CORE", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    for i, alert in enumerate(recent_alerts[:5]):
        cv2.putText(image, alert, (20, 85 + (i * 30)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    cv2.putText(image, f"FPS: {int(fps)}", (wd - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(image, "AWS S3: Connected", (wd - 180, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imshow('👁 NetraFlow',image)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()