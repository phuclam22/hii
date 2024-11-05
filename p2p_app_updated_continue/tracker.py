import socket
import threading
import json

class Tracker:
    def __init__(self, host='localhost', port=6881):
        self.host = host
        self.port = port
        self.clients = {}

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Tracker started on {self.host}:{self.port}")
        
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        try:
            request = json.loads(client_socket.recv(1024).decode('utf-8'))
            command = request.get('command')

            if command == 'register':
                self.register_client(request)
            elif command == 'discover':
                self.discover_clients(client_socket)
            elif command == 'ping':
                self.ping_client(request, client_socket)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def register_client(self, request):
        peer_id = request['peer_id']
        port = request['port']
        files = request['files']

        # Lưu thông tin máy khách vào từ điển với peer_id
        self.clients[peer_id] = {'ip': self.host, 'port': port, 'files': files}
        print(f"Registered client {peer_id} with files: {files}")

    def discover_clients(self, client_socket):
        response = {'clients': [{'peer_id': peer_id, 'ip': info['ip'], 'port': info['port'], 'files': info['files']} for peer_id, info in self.clients.items()]}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

    def ping_client(self, request, client_socket):
        response = {'status': 'alive'}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

if __name__ == "__main__":
    tracker = Tracker()
    tracker.start()
