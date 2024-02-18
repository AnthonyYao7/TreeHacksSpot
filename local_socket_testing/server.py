import socket
from threading import Thread, Lock
import struct
from enum import Enum
from ultralytics import YOLO
from collections import deque
import time
import cv2

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
        print("Waiting for file")
        while len(mq) == 0: time.sleep(1)

        command = mq.popleft()
        sock.sendall((command + '\n').encode('utf-8'))


class RobotStates(Enum):
    WAITING_FOR_COMMAND = 1  # commands are of the form take me to something
    TARGETING = 2  # back and forth between robot and server with yolo and images
    WALKING = 3  # robot is facing towards the target and will start walking


# robot_state = RobotStates.TARGETING
# robot_state_mutex = Lock()

file_handler_threads = []

model = YOLO("yolov8n.pt")

translation = None
most_recent_classes = None
most_recent_boxes = None
target_class = None


def int_from_bytes(bt):
    return struct.unpack('<I', bt)[0]


def handle_new_file(file):
    global target_class

    ext = file.split('.')[1]

    # with robot_state_mutex:
    if ext == 'jpg':
        # if robot_state != RobotStates.TARGETING:
        #     print("JPG files only relevant in targeting stage")
        #     return

        results = model(file)[0]
        boxes = results.boxes.xyxy.numpy()
        class_names = results.names
        pred = results.boxes.cls.numpy()

        global translation, most_recent_boxes, most_recent_classes
        if translation is None:
            translation = class_names

        most_recent_classes = pred
        most_recent_boxes = boxes

        print(target_class)

        if target_class is None:
            return

        ind = None

        for i, cl in enumerate(pred):
            if cl == target_class:
                ind = i
                break

        if ind is None:
            print("im fucked")

        image = cv2.imread(file)
        w = image.shape[1]

        rel_bbox = most_recent_boxes[ind]
        dims = results.orig_shape
        x_hat = (rel_bbox[0] + rel_bbox[2]) // 20
        mq.append(f"move_towards_point{x_hat},{w}")

        """
        Call yolo on jpg and get bounding boxes and return response to spot
        """

    elif ext == 'wav':
        # if robot_state != RobotStates.WAITING_FOR_COMMAND:
        #     print("WAV files only relevant when waiting for commands")
        #     return
        """
        Send wav file to whisper api for transcription
        """
        from openai import OpenAI
        client = OpenAI(api_key="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")
        audio_file = open(file, "rb")
        vocal_query = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )

        obj_arr = [translation[most_recent_classes[i]] for i in range(len(most_recent_classes))]
        # translation: number to object
        prompt = f"{obj_arr} \n YOUR TASK: given the previous array of strings denoting objects detected in an image, isolate only one object that matches the object specified by the following verbal query: \"{vocal_query}\" \n THIS IS VERY IMPORTANT: ONLY RETURN THE NUMERICAL 0-BASED INDEX OF THE FIRST SUCH RELEVANT OBJECT IN THE ARRAY, WITH NO OTHER TEXT IN YOUR OUTPUT"
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}]
        )
        resp_ret = response.choices[0].message.content
        # for term in translation:
        try:
            # if translation[term] == translation[most_recent_classes[int(resp_ret)]]:
            target_class = int(most_recent_classes[int(resp_ret)])
            print('aowiefjwiaofj', target_class)
        except ValueError:
            print("errored out")
            print(resp_ret)
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

        message_sending_thread.start()

        while True:
            command = input("Start process:")
            if command == "ligma":
                break

            seq = ['take_image',
                   'start_asr',
                   'take_image',
                   'take_image',
                   'take_image',
                   'take_image',
                   'take_image',
                   'take_image',
                   'take_image',
                   'take_image',
                   'take_image']

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
