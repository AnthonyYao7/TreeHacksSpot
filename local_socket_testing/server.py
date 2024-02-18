import socket
from threading import Thread, Lock
import struct
from enum import Enum
from ultralytics import YOLO
from collections import deque
import time

ROTATION_ANGLE = {
    'back_fisheye_image': 0,
    'frontleft_fisheye_image': -78,
    'frontright_fisheye_image': -102,
    'left_fisheye_image': 0,
    'right_fisheye_image': 180
}


mq = deque()


def send_commands(sock):
    global mq
    while True:
        while len(mq) == 0: time.sleep(1)

        command = mq.popleft()
        sock.sendall((command + '\n').encode('utf-8'))


class RobotStates(Enum):
    WAITING_FOR_COMMAND = 1  # commands are of the form take me to something
    TARGETING = 2  # back and forth between robot and server with yolo and images
    WALKING = 3  # robot is facing towards the target and will start walking


robot_state = RobotStates.TARGETING
robot_state_mutex = Lock()

file_handler_threads = []

model = YOLO("yolov8n.pt")

translation = None
most_recent_classes = None
most_recent_boxes = None


def int_from_bytes(bt):
    return struct.unpack('<I', bt)[0]


def handle_new_file(file):
    ext = file.split('.')[1]

    with robot_state_mutex:
        if ext == 'jpg':
            if robot_state != RobotStates.TARGETING:
                print("JPG files only relevant in targeting stage")
                return

            results = model(file)[0]
            boxes = results.boxes.xyxy.numpy()
            class_names = results.names
            pred = results.boxes.cls.numpy()

            global translation, most_recent_boxes, most_recent_classes
            if translation is None:
                translation = class_names

            most_recent_classes = pred
            most_recent_boxes = boxes

            """
            Call yolo on jpg and get bounding boxes and return response to spot
            """

        elif ext == 'wav':
            if robot_state != RobotStates.WAITING_FOR_COMMAND:
                print("WAV files only relevant when waiting for commands")
                return



            """
            Send wav file to whisper api for transcription
            """

        else:
            pass


def read_bytes(sock, n):
    data = b''

    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            print("Connection closed by the client during data reception.")
            break
        data += chunk

    return data


def read_from_client(client_socket, address, file_name_prefix):
    while True:
        filename_length_bytes = client_socket.recv(4)

        if not filename_length_bytes:
            print("Connection closed by the client.")
            break

        filename_length = int_from_bytes(filename_length_bytes)
        filename = read_bytes(client_socket, filename_length).decode('utf-8')
        file_content_length_bytes = client_socket.recv(4)

        if not filename_length_bytes:
            print("Connection closed by the client.")
            break

        file_content_length = int_from_bytes(file_content_length_bytes)
        file_content = read_bytes(client_socket, file_content_length)
        file_name = f"{file_name_prefix}/{filename}"

        with open(file_name, 'wb') as file:
            file.write(file_content)

        file_handler_threads.append(
            Thread(target=handle_new_file, args=(file_name,)))
        file_handler_threads[-1].start()


def handle_client_connection(client_socket: socket.socket, address, file_name_prefix):
    with client_socket:
        print(f"Connection from {address} has been established.")

        # Create and start the reading thread
        reading_thread = Thread(
            target=read_from_client,
            args=(client_socket, address, file_name_prefix))
        reading_thread.start()

        message_sending_thread = Thread(
            target=send_commands,
            args=(client_socket,)
        )

        while True:
            command = input("Start process:")
            if command == "ligma":
                break

            seq = ['take_image',
                   'start_asr',
                   'move_towards_point',
                   'take_image',
                   'move_towards_point']

            for inst in seq:
                mq.append(inst)

        reading_thread.join()
        message_sending_thread.join()


def start_server(host, port, file_name_prefix):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen()

        print(f"Server listening on {host}:{port}")

        # only accept one connection, end after one connection
        client_socket, address = server_socket.accept()
        handle_client_connection(client_socket, address, file_name_prefix)


HOST = '0.0.0.0'
PORT = 8080
FILE_NAME_PREFIX = 'files'


if __name__ == "__main__":
    start_server(HOST, PORT, FILE_NAME_PREFIX)
