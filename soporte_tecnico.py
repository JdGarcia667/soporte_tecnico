import socket
import threading
import time
import os

def handle_client(client_socket, address, messages, file):
    while True:
        data = client_socket.recv(1024).decode('utf-8')
        if not data:
            break

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        message = f"{current_time} ({address[0]}): {data}"
        messages.append(message)

        with open(file, 'a') as f:
            f.write(message + "\n")

        response = f"Mensaje recibido a las {current_time}\n"
        client_socket.send(response.encode('utf-8'))

    client_socket.close()

def start_server():
    host = '0.0.0.0'
    port = 12345

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)

    print(f"Escuchando en {host}:{port}")

    messages = []
    file = "mensajes.txt"

    while True:
        client_socket, addr = server.accept()
        print(f"Conexión entrante desde {addr[0]}:{addr[1]}")

        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr, messages, file))
        client_handler.start()

def start_client():
    nodos = {
        'A': '192.168.132.131',
        'B': '192.168.132.128',
        'C': '192.168.132.132',
        #'D': '192.168.108.133'
    }

    client_socket = None
    selected_node = None

    def connect_to_node(node):
        nonlocal client_socket, selected_node
        if client_socket:
            client_socket.close()

        host = nodos[node]
        port = 12345
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        selected_node = node

        print(f"Conectado a {node}: {host}")

    def receive_messages():
        while True:
            if not client_socket:
                continue
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    print(f"Mensaje recibido del nodo {selected_node}: {message}")
            except:
                break

    receiver_thread = threading.Thread(target=receive_messages, daemon=True)
    receiver_thread.start()

    while True:
        print("Nodos disponibles:")
        for key, value in nodos.items():
            print(f"{key}: {value}")

        selected_node = input("Elige el nodo al que quieres enviar mensajes (o 'exit' para salir): ").upper()
        if selected_node == 'EXIT':
            break

        if selected_node not in nodos:
            print("Opción no válida. Intenta de nuevo.")
            continue

        connect_to_node(selected_node)

        file_a = f"mensajes_maquina_{selected_node.lower()}.txt"

        if not os.path.exists(file_a):
            with open(file_a, 'w'):
                pass

        while True:
            message = input("Escribe tu mensaje (o 'cambiar' para cambiar de nodo, 'exit' para salir): ")
            if message.lower() == 'cambiar':
                break
            if message.lower() == 'exit':
                client_socket.close()
                return

            with open(file_a, 'a') as f:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                message_with_time = f"{current_time}: {message}\n"
                f.write(message_with_time)

            client_socket.send(message.encode('utf-8'))

if _name_ == "_main_":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    time.sleep(1)  # Esperar un momento para asegurarse de que el servidor está en funcionamiento

    start_client()
