import cv2
from dotenv import load_dotenv
import os
from CameraHandler import Camera
from multiprocessing import Process


load_dotenv()



DEFAULT_URL = os.getenv("DEFAULT_CAMERA_URL")
MAC_ADDRESS = os.getenv("MAC_ADDRESS")
CAMERA_PASSWORD = os.getenv("CAMERA_PASSWORD")

def stream_handler(camera = None):
    if not camera:
        camera = Camera(MAC_ADDRESS)
    camera_ip = camera.get_ip()
    print(camera_ip)
    stream_address = DEFAULT_URL.format(CAMERA_PASSWORD, camera_ip)
    print(stream_address)

    try:
        capture = cv2.VideoCapture(stream_address, cv2.CAP_FFMPEG)

        if not capture.isOpened():
            print("Capture did not work womp womp")
            exit()



        while True:
            running, frame = capture.read()
            frame = cv2.resize(frame, (1600, 900))
            if not running:
                print("lost connection :(")
                break

            cv2.imshow("Camera :D", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Interrompido")
    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    proc = Process(target=stream_handler)
    proc.start()
    proc.join()
    # stream_handler()





