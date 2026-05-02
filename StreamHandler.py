import atexit
import os
import pathlib as pl
import shutil
import subprocess
import time
from multiprocessing import Process
from threading import Thread, Lock
import numpy as np
import cv2
import imutils
from dotenv import load_dotenv
from datetime import datetime

from CameraHandler import Camera



load_dotenv()



DEFAULT_URL = os.getenv("DEFAULT_CAMERA_URL")
MAC_ADDRESS = os.getenv("MAC_ADDRESS")
CAMERA_PASSWORD = os.getenv("CAMERA_PASSWORD")
clipping = False
clip_lock = Lock()


def processFrame(frame):
    frame = cv2.resize(frame, (850, 450))
    unprocessed_frame = frame.copy()

    ignored_points = [
    [100, 100], # Superior Esquerdo
    [230, 100], # Superior Direito
    [230, 195], # Inferior Direito
    [100, 195]  # Inferior Esquerdo
    ]

    censor_square = np.array([ignored_points], dtype=np.int32)


    frame = cv2.fillPoly(frame, censor_square, 0)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.GaussianBlur(frame, (5,5), 0)
    # cv2.rectangle(frame, (115, 165), (350, 300), (0, 255, 0), 1)
    return frame, unprocessed_frame

def subtract_frames(frame1, frame2):
    diff = cv2.absdiff(frame1, frame2)
    _, thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
    return diff, thresh


def start_ffmpeg(stream_address):
    ffmpeg_command = [
    'ffmpeg',
    '-rtsp_transport', 'udp',
    '-i', stream_address,
    '-c', 'copy',
    '-f', 'segment',
    '-segment_time', '60',
    '-segment_wrap', '6',
    '-reset_timestamps', '1',
    './temprecordings/buffer_%02d.mkv'
    ]
    print("Started Recording Process")
    buffer_path = pl.Path("./temprecordings/")
    buffer_path.mkdir(parents=True, exist_ok=True)
    global recorder_process
    recorder_process = subprocess.Popen(
    ffmpeg_command, 
    stdout=subprocess.DEVNULL, 
    stderr=subprocess.DEVNULL
    )

def save_clip():
    with clip_lock:
        global clipping
        if clipping:
            return
        else:
            clipping = True
    detection_time = datetime.now()
    detection_time = detection_time.strftime("%Y-%m-%d_%H-%M-%S")

    print("Clipping started, sleeping for 65 seconds")
    time.sleep(65)
    buffer_folder = pl.Path("./temprecordings/")
    recordings_folder = pl.Path("./recordings")

    recordings_folder.mkdir(parents=True, exist_ok=True)
    recording_file = pl.Path(recordings_folder / f"movimento_{detection_time}.mkv")
    buffer_files = list(buffer_folder.glob("buffer_*.mkv"))
    buffer_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    motion_file = buffer_files[1]
    shutil.copy(motion_file, recording_file)
    print(f"Clip written to {recording_file}")
    clipping = False


def start_capture(stream_address):
    while True:
        try:
            capture = cv2.VideoCapture(stream_address, cv2.CAP_FFMPEG)
            if not capture.isOpened():
                print("Capture did not work womp womp")
                time.sleep(2)
                continue
            return capture
        except KeyboardInterrupt:
            exit()



def stream_handler(camera = None):
    if not camera:
        camera = Camera(MAC_ADDRESS)
    camera_ip = camera.get_ip()
    print(camera_ip)
    stream_address = DEFAULT_URL.format(CAMERA_PASSWORD, camera_ip)
    print(stream_address)

    try:
        capture = start_capture(stream_address)
        firstFrame = None
        cv2.namedWindow("Camera :D", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Camera :D", 1600, 900)
        cv2.namedWindow("Camera POV", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Camera POV", 1600, 900)
        motion_time = time.time()
        start_ffmpeg(stream_address)
        while True:
            motion_detected = False
            running, frame = capture.read()

            if not running:
                capture.release()
                time.sleep(.2)
                capture = start_capture(stream_address)
                continue

            if frame is not None:
                frame, unprocessed_frame = processFrame(frame)
                if firstFrame is None:
                    firstFrame = frame.astype("float")
                else:
                    diff, thresh = subtract_frames(cv2.convertScaleAbs(firstFrame), frame)
                    dilated_frame = cv2.dilate(thresh, None, iterations=2)
                    cnts = cv2.findContours(dilated_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnts = imutils.grab_contours(cnts)

                    frame_moving = False
                    for c in cnts:
                        if cv2.contourArea(c) < 900:
                            continue
                        else:
                            frame_moving = True
                            (x, y, w,h) = cv2.boundingRect(c)
                            cv2.rectangle(unprocessed_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            if time.time() - motion_time > 10:
                                motion_detected = True
                            motion_time = time.time()
    
                    if not frame_moving:
                        cv2.accumulateWeighted(frame, firstFrame, 0.05)

            
            cv2.imshow("Camera :D", unprocessed_frame)
            if motion_detected:
                if not clipping:
                    clippingThread = Thread(target=save_clip, daemon=True)
                    clippingThread.start()
                print("MOTION DETECTED WEEE WOOOO") #Place holder for clipping logic
            cv2.imshow("Camera POV", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Interrompido")
    finally:
        capture.release()
        cv2.destroyAllWindows()
        recorder_process.terminate()



if __name__ == "__main__":
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    proc = Process(target=stream_handler)
    proc.start()
    proc.join()
    # stream_handler()