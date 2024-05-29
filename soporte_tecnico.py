import socket
import threading
import time
import os

# Función para manejar las conexiones de los clientes al servidor
def handle_client(client_socket, address, messages, file):
    while True:
        # Recibir datos del cliente
        data = client_socket.recv(1024).decode('utf-8')
        if not data:
            break

        # Obtener la hora actual
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # Crear el mensaje con la hora, la dirección IP del cliente y los datos recibidos
        message = f"{current_time} ({address[0]}): {data}"
        # Agregar el mensaje a la lista de mensajes
        messages.append(message)

        # Escribir el mensaje en un archivo
        with open(file, 'a') as f:
            f.write(message + "\n")

        # Enviar una respuesta al cliente
        response = f"Mensaje recibido a las {current_time}\n"
        client_socket.send(response.encode('utf-8'))

    # Cerrar el socket del cliente cuando se completa la comunicación
    client_socket.close()

# Función para iniciar el servidor
def start_server():
    host = '0.0.0.0'
    port = 12345

    # Crear un socket TCP/IP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enlazar el socket al host y al puerto
    server.bind((host, port))
    # Escuchar conexiones entrantes
    server.listen(5)

    # Imprimir un mensaje indicando que el servidor está escuchando
    print(f"Escuchando en {host}:{port}")

    # Lista para almacenar los mensajes recibidos
    messages = []
    # Nombre del archivo donde se guardarán los mensajes
    file = "mensajes.txt"

    # Bucle para aceptar conexiones entrantes de clientes
    while True:
        # Aceptar una conexión entrante
        client_socket, addr = server.accept()
        # Imprimir un mensaje indicando la conexión entrante
        print(f"Conexión entrante desde {addr[0]}:{addr[1]}")

        # Crear un nuevo hilo para manejar la comunicación con el cliente
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr, messages, file))
        client_handler.start()

# Función para iniciar el cliente
def start_client():
    # Diccionario que mapea nombres de nodos a direcciones IP
    nodos = {
        'A': '192.168.132.131',
        'B': '192.168.132.128',
        'C': '192.168.132.132',
        #'D': '192.168.108.133'
    }

    client_socket = None
    selected_node = None

    # Función para conectarse a un nodo específico
    def connect_to_node(node):
        nonlocal client_socket, selected_node
        if client_socket:
            client_socket.close()

        # Obtener la dirección IP del nodo seleccionado
        host = nodos[node]
        port = 12345
        # Crear un socket TCP/IP
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Conectarse al nodo seleccionado
        client_socket.connect((host, port))
        selected_node = node

        # Imprimir un mensaje indicando la conexión exitosa
        print(f"Conectado a {node}: {host}")

    # Función para recibir mensajes del nodo
    def receive_messages():
        while True:
            # Verificar si hay un socket válido
            if not client_socket:
                continue
            try:
                # Recibir un mensaje del nodo
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    # Imprimir el mensaje recibido
                    print(f"Mensaje recibido del nodo {selected_node}: {message}")
            except:
                break

    # Crear un hilo para recibir mensajes del nodo
    receiver_thread = threading.Thread(target=receive_messages, daemon=True)
    receiver_thread.start()

    # Bucle para seleccionar un nodo y enviar mensajes
    while True:
        print("Nodos disponibles:")
        for key, value in nodos.items():
            print(f"{key}: {value}")

        # Solicitar al usuario que seleccione un nodo
        selected_node = input("Elige el nodo al que quieres enviar mensajes (o 'exit' para salir): ").upper()
        if selected_node == 'EXIT':
            break

        # Verificar si el nodo seleccionado es válido
        if selected_node not in nodos:
            print("Opción no válida. Intenta de nuevo.")
            continue

        # Conectarse al nodo seleccionado
        connect_to_node(selected_node)

        # Nombre del archivo donde se guardarán los mensajes enviados al nodo
        file_a = f"mensajes_maquina_{selected_node.lower()}.txt"

        # Crear el archivo si no existe
        if not os.path.exists(file_a):
            with open(file_a, 'w'):
                pass

        # Bucle para enviar mensajes al nodo seleccionado
        while True:
            # Solicitar al usuario que ingrese un mensaje
            message = input("Escribe tu mensaje (o 'cambiar' para cambiar de nodo, 'exit' para salir): ")
            if message.lower() == 'cambiar':
                break
            if message.lower() == 'exit':
                client_socket.close()
                return

            # Escribir el mensaje en el archivo
            with open(file_a, 'a') as f:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                message_with_time = f"{current_time}: {message}\n"
                f.write(message_with_time)

            # Enviar el mensaje al nodo
            client_socket.send(message.encode('utf-8'))

# Función principal para iniciar el servidor y el cliente
if __name__ == "__main__":
    # Crear un hilo para iniciar el servidor
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Esperar un momento para asegurarse de que el servidor esté en funcionamiento
    time.sleep(1)

    # Iniciar el cliente
    start_client()
