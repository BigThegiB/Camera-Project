import requests
from dotenv import load_dotenv
import os
from pathlib import Path
import contextlib
import subprocess

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def Convert2MP4(input_path):
    output_path = input_path.with_suffix('.mp4')
    try:
        ffmpeg_command = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'copy',
            '-c:a', 'aac',
            str(output_path)
        ]
        subprocess.run(ffmpeg_command, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Erro na conversão: {e}, retornando mkv original")
        return input_path


def SendWebhook(files : dict):
    motion_frame = files["motion_frame"]
    part_1_mkv = files["part1"]
    part_2_mkv = files["part2"]

    part_1 = Convert2MP4(part_1_mkv)

    part_2 = Convert2MP4(part_2_mkv)




    with contextlib.ExitStack() as stack:
        files_upload = [
            ("files[0]", stack.enter_context(open(motion_frame, 'rb'))),
            ("files[1]", stack.enter_context(open(part_1, 'rb'))),
            ("files[2]", stack.enter_context(open(part_2, 'rb'))),
        ]
        message = {"content": "@everyone MOTION DETECTED!"}
        response = requests.post(WEBHOOK_URL, data=message, files=files_upload)
    if response.ok:
        print("Mensagem enviada ao Discord com sucesso!")
        if part_1.suffix == '.mp4':
            part_1.unlink(missing_ok=True)
        if part_2.suffix == '.mp4':
            part_2.unlink(missing_ok=True)
    else:
        print(f"Falha ao enviar mensagem: {response.status_code} - {response.text}")


    


    