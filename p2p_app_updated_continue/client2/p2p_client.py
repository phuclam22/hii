import socket
import threading
import json
import os

class Client:
    def __init__(self, peer_id, tracker_host='localhost', tracker_port=6881):
        self.peer_id = peer_id
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.files = []
        self.connected = True
        self.port = 0  # Cổng của máy khách (sẽ được chọn ngẫu nhiên)
        self.server_socket = None  # Server socket cho kết nối tải tệp
    
    def start_file_server(self):
        """Bắt đầu server socket để lắng nghe yêu cầu tải tệp từ các máy khách khác"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', 0))  # Chọn một cổng ngẫu nhiên
        self.server_socket.listen(5)
        self.port = self.server_socket.getsockname()[1]
        print(f"File server started on port {self.port}")
        
        # Bắt đầu một luồng riêng để xử lý các yêu cầu tải tệp
        threading.Thread(target=self.handle_incoming_connections, daemon=True).start()

    def handle_incoming_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=self.handle_client_request, args=(client_socket,), daemon=True).start()

    def handle_client_request(self, client_socket):
        """Xử lý yêu cầu tải tệp từ một máy khách khác"""
        try:
            request = json.loads(client_socket.recv(1024).decode('utf-8'))
            filename = request.get("filename")
            print(f"Received request for file: {filename}")

            if filename in self.files:
                with open(f"./shared_files/{filename}", "rb") as f:
                    data = f.read(1024)
                    while data:
                        client_socket.send(data)
                        data = f.read(1024)
                print(f"File {filename} sent successfully.")
            else:
                print(f"File {filename} not found.")
        except Exception as e:
            print(f"Error handling file request: {e}")
        finally:
            client_socket.close()

    def connect_to_tracker(self):
        print("Connecting to tracker...")
        self.connected = True
        print("Connected to tracker.")
    
    def sign_in(self):
        print("Signing in...")
        self.connect_to_tracker()
        self.publish_files()

    def sign_out(self):
        self.connected = False
        print("Signed out from tracker.")
    
    def publish_files(self):
        print("Publishing files...")
        self.files = os.listdir('./shared_files')
        response = self.send_request({
            "command": "register", 
            "peer_id": self.peer_id, 
            "files": self.files, 
            "port": self.port  # Đảm bảo gửi đúng cổng máy khách
        })
        print("Publish response:", response)

    def fetch_file(self, filename):
        print(f"Fetching file: {filename}")
        peers = self.send_request({"command": "discover"})["clients"]
        file_found = False

        for peer in peers:
            if filename in peer["files"] and peer["peer_id"] != self.peer_id:
                peer_ip = peer["ip"]
                peer_port = peer["port"]
                print(f"Attempting to download {filename} from {peer_ip}:{peer_port}")
                threading.Thread(target=self.download_file, args=(peer_ip, peer_port, filename)).start()
                file_found = True
                break

        if not file_found:
            print("File not found on any connected peers.")
    
    def download_file(self, ip, port, filename):
        print(f"Connecting to {ip}:{port} to download {filename}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(json.dumps({"command": "download", "filename": filename}).encode('utf-8'))
                
                # Đảm bảo thư mục 'shared_files' tồn tại
                if not os.path.exists('./shared_files'):
                    os.makedirs('./shared_files')
                
                # Lưu tệp vào thư mục shared_files của máy khách
                with open(f'./shared_files/{filename}', 'wb') as f:
                    while True:
                        data = s.recv(1024)
                        if not data:
                            break
                        f.write(data)
                print(f"Downloaded {filename} successfully to shared_files.")
                
                # Cập nhật danh sách tệp sau khi tải thành công
                self.files.append(filename)
                
        except ConnectionRefusedError:
            print(f"Connection refused when trying to download {filename}. The server might not be running.")
        except Exception as e:
            print(f"Error downloading file: {e}")
    
    def send_request(self, data):
        print("Sending request to tracker:", data)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.tracker_host, self.tracker_port))
                s.sendall(json.dumps(data).encode('utf-8'))
                response = json.loads(s.recv(1024).decode('utf-8'))
            print("Received response from tracker:", response)
            return response
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    def command_shell(self):
        print("Starting command shell...")
        print("Enter commands: 'sign_in', 'sign_out', 'publish', 'fetch <filename>', 'discover', 'ping'")
        while self.connected:
            command = input(">> ").strip().split()
            if not command:
                continue
            if command[0] == 'sign_in':
                self.sign_in()
            elif command[0] == 'sign_out':
                self.sign_out()
                break
            elif command[0] == 'publish':
                self.publish_files()
            elif command[0] == 'fetch' and len(command) > 1:
                self.fetch_file(command[1])
            elif command[0] == 'discover':
                self.perform_discover()
            elif command[0] == 'ping':
                self.perform_ping()
            else:
                print("Invalid command. Please try again.")

    def perform_discover(self):
        print("Performing discover...")
        peers = self.send_request({"command": "discover"})
        for peer in peers.get('clients', []):
            print(f"Peer ID: {peer['peer_id']}, IP: {peer['ip']}, Port: {peer['port']}, Files: {peer['files']}")

    def perform_ping(self):
        print("Performing ping...")
        response = self.send_request({"command": "ping", "peer_id": self.peer_id})
        print(f"Ping response: {response}")

if __name__ == "__main__":
    peer_id = input("Enter a unique peer ID for this client: ")
    client = Client(peer_id=peer_id)
    client.start_file_server()  # Bắt đầu server để lắng nghe yêu cầu tải tệp
    client.command_shell()
