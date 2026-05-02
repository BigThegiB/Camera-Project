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
from DiscordHandler import SendWebhook


load_dotenv()



DEFAULT_URL = os.getenv("DEFAULT_CAMERA_URL")
MAC_ADDRESS = os.getenv("MAC_ADDRESS")
CAMERA_PASSWORD = os.getenv("CAMERA_PASSWORD")
OVERRIDE_STREAM_ADDRESS = os.getenv("OVERRIDE_STREAM_ADDRESS")
OVERRIDE_DETECTION_ADDRESS = os.getenv("OVERRIDE_DETECTION_ADDRESS")
# 1 - Qualidade mais alta, 2 - Qualidade mais baixa
STREAM_SERVER_LANE = 1
DETECTION_SERVER_LANE = 2
MAXIMO_MOVIMENTO_CONSTANTE = 30
SERVER_IP_OVERRIDE = False
CREATE_WINDOWS = True
SEND_WEBHOOKS = True

clipping = False
clip_lock = Lock()


def processFrame(frame):
    frame = cv2.resize(frame, (850, 450))
    unprocessed_frame = frame.copy()

    ignored_points = [
    [130, 90], # Superior Esquerdo
    [280, 90], # Superior Direito
    [280, 205], # Inferior Direito
    [130, 205]  # Inferior Esquerdo
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
    recorder_process = subprocess.Popen(
    ffmpeg_command, 
    stdout=subprocess.DEVNULL, 
    stderr=subprocess.DEVNULL
    )
    return recorder_process

def get_current_buffer(buffer_folder, old_file = None):
    file_is_new = False
    while not file_is_new:
        buffer_files = list(buffer_folder.glob("buffer_*.mkv"))
        buffer_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        current_file = buffer_files[0]
        if current_file != old_file:
            file_is_new = True
        time.sleep(2)
    
    file_finished = False
    while not file_finished:
        buffer_files = list(buffer_folder.glob("buffer_*.mkv"))
        buffer_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        next_file = buffer_files[0]
        if current_file != next_file:
            return current_file
        time.sleep(2)



def save_clip(detected_frame):
    with clip_lock:
        global clipping
        if clipping:
            return
        else:
            clipping = True
    
    unformatted_time = datetime.now()
    detection_datetime = unformatted_time.strftime("%Y-%m-%d_%H-%M-%S")
    detection_time = unformatted_time.strftime("%H-%M-%S")



    print(f"Clipping começou as {detection_time}, esperando os proximos 2 arquivos")
    
    buffer_folder = pl.Path("./temprecordings/")
    recordings_folder = pl.Path("./recordings")

    recordings_folder.mkdir(parents=True, exist_ok=True)
    frameFile = pl.Path(recordings_folder / f"{detection_datetime}-frame_detectado.jpg")
    cv2.imwrite(str(frameFile), detected_frame)
    motion_file1 = get_current_buffer(buffer_folder)
    motion_file1_destination = recordings_folder / f"{detection_datetime}-movimento_parte1.mkv"
    print(f"Parte 1 terminada, copiando parte 1, arquivo: {motion_file1}")
    shutil.copy(motion_file1, motion_file1_destination)

    motion_file2 = get_current_buffer(buffer_folder, motion_file1)
    motion_file2_destination = recordings_folder / f"{detection_datetime}-movimento_parte2.mkv"
    print(f"Parte 2 terminada, copiando parte 2, arquivo: {motion_file2}")
    shutil.copy(motion_file2, motion_file2_destination)

    discord_dict = {
        "motion_frame": frameFile,
        "part1": motion_file1_destination,
        "part2": motion_file2_destination

    }

    if SEND_WEBHOOKS:
        SendWebhook(discord_dict)

    print(f"Clip written to {recordings_folder}")
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
    if SERVER_IP_OVERRIDE:
        print("Usando IP predeterminado")
        stream_address = OVERRIDE_STREAM_ADDRESS
        detection_address = OVERRIDE_DETECTION_ADDRESS
    else:
        if not camera:
            camera = Camera(MAC_ADDRESS)
        print("Buscando IP da camera")
        camera_ip = camera.get_ip()
        print(camera_ip)
        stream_address = DEFAULT_URL.format(CAMERA_PASSWORD, camera_ip, STREAM_SERVER_LANE)
        detection_address = DEFAULT_URL.format(CAMERA_PASSWORD, camera_ip, DETECTION_SERVER_LANE)
    print(stream_address)
    print(detection_address)

    try:
        recorder_process = None
        capture = start_capture(detection_address)
        firstFrame = None
        if CREATE_WINDOWS:
            cv2.namedWindow("Camera :D", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Camera :D", 1366, 768)
            cv2.namedWindow("Camera POV", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Camera POV", 1600, 900)
        motion_time = time.time()
        movimento_constante = None
        recorder_process = start_ffmpeg(stream_address)
        while True:
            motion_detected = False
            running, frame = capture.read()

            if not running:
                capture.release()
                time.sleep(.2)
                capture = start_capture(detection_address)
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

                    if frame_moving:
                        if movimento_constante is None:
                            movimento_constante = time.time()
                        elif time.time() - movimento_constante > MAXIMO_MOVIMENTO_CONSTANTE:
                            print("Movimento constante por mais de 30 segundos, reiniciando frame de referencia")
                            firstFrame = frame.astype("float")
                            movimento_constante = None


                    else:
                        cv2.accumulateWeighted(frame, firstFrame, 0.05)
                        movimento_constante = None

            if CREATE_WINDOWS:
                cv2.imshow("Camera :D", unprocessed_frame)
                cv2.imshow("Camera POV", frame)
            if motion_detected:
                if not clipping:
                    clippingThread = Thread(target=save_clip,args=(unprocessed_frame,), daemon=True)
                    clippingThread.start()

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                if not clipping:
                    clippingThread = Thread(target=save_clip,args=(unprocessed_frame,), daemon=True)
                    clippingThread.start()

    except KeyboardInterrupt:
        print("Interrompido")
    finally:
        capture.release()
        cv2.destroyAllWindows()
        if recorder_process is not None:
            recorder_process.terminate()



if __name__ == "__main__":
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    proc = Process(target=stream_handler)
    proc.start()
    proc.join()
    # stream_handler()