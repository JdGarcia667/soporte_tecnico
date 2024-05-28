import socket
import threading
import time
import os
import mysql.connector
from queue import Queue, Empty
import json

# Conectar a la base de datos MariaDB
def connect_to_db():
    return mysql.connector.connect(
        host='your_db_host',
        user='your_db_user',
        password='your_db_password',
        database='your_db_name'
    )

def handle_client(client_socket, address, messages, file, nodos, command_queue):
    db_connection = connect_to_db()
    cursor = db_connection.cursor()

    while True:
        data = client_socket.recv(1024).decode('utf-8')
        if not data:
            break

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        message = f"{current_time} ({address[0]}): {data}"
        messages.append(message)

        with open(file, 'a') as f:
            f.write(message + "\n")

        # Suponemos que los mensajes contienen comandos SQL
        try:
            cursor.execute(data)
            db_connection.commit()

            # Agregar el comando a la cola de comandos para notificar a otros nodos
            command_queue.put(data)

            response = f"Comando ejecutado localmente a las {current_time}\n"
        except Exception as e:
            response = f"Error ejecutando el comando: {e}\n"

        client_socket.send(response.encode('utf-8'))

    cursor.close()
    db_connection.close()
    client_socket.close()

def notify_other_nodes(command, origin_node, nodos, retry_queue):
    for node, ip in nodos.items():
        if ip == origin_node:
            continue
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, 12345))
            client_socket.send(command.encode('utf-8'))
            ack = client_socket.recv(1024).decode('utf-8')
            if ack == 'ACK':
                print(f"Confirmación recibida de {node} ({ip})")
            client_socket.close()
        except Exception as e:
            print(f"No se pudo conectar a {node} ({ip}): {e}")
            retry_queue.put((command, ip))

def retry_pending_commands(retry_queue, nodos):
    while True:
        try:
            command, ip = retry_queue.get(timeout=10)
            for _ in range(3):  # Intentar reenvío 3 veces
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((ip, 12345))
                    client_socket.send(command.encode('utf-8'))
                    ack = client_socket.recv(1024).decode('utf-8')
                    if ack == 'ACK':
                        print(f"Confirmación recibida después de reintento de {ip}")
                        break
                    client_socket.close()
                except Exception as e:
                    print(f"Reintento fallido para {ip}: {e}")
                    time.sleep(5)  # Esperar antes de reintentar
            else:
                print(f"Fallo permanente en la replicación a {ip}")
        except Empty:
            continue

def start_server():
    host = '0.0.0.0'
    port = 12345

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)

    print(f"Escuchando en {host}:{port}")

    messages = []
    file = "mensajes.txt"
    nodos = {
        'A': '192.168.132.131',
        'B': '192.168.132.128',
        'C': '192.168.132.132',
        #'D': '192.168.108.133'
    }
    command_queue = Queue()
    retry_queue = Queue()

    def notify_others():
        while True:
            command = command_queue.get()
            if command is None:
                break
            notify_other_nodes(command, '0.0.0.0', nodos, retry_queue)
    
    notifier_thread = threading.Thread(target=notify_others, daemon=True)
    notifier_thread.start()

    retry_thread = threading.Thread(target=retry_pending_commands, args=(retry_queue, nodos), daemon=True)
    retry_thread.start()

    while True:
        client_socket, addr = server.accept()
        print(f"Conexión entrante desde {addr[0]}:{addr[1]}")

        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr, messages, file, nodos, command_queue))
        client_handler.start()

def start_client():
    nodos = {
        'A': '192.168.108.130',
        'B': '192.168.108.131',
        'C': '192.168.108.132',
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
                    if message == 'ACK':
                        continue
                    print(f"Mensaje recibido del nodo {selected_node}: {message}")
                    # Enviar ACK de confirmación
                    client_socket.send('ACK'.encode('utf-8'))
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

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    time.sleep(1)  # Esperar un momento para asegurarse de que el servidor está en funcionamiento

    start_client()
