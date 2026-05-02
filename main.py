import os
from multiprocessing import Process
from StreamHandler import stream_handler


if __name__ == "__main__":
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    proc = Process(target=stream_handler)
    proc.start()
    proc.join()