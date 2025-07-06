import socket
import threading
import enum
import pickle
import time

# Netzwerkeinstellungen
ENCODING = 'utf-8'
CHAT_PORT = 9000
DISCOVERY_GROUP_IP = '224.1.1.1'
DISCOVERY_PORT = 9001
DISCOVERY_ADDRESS = (DISCOVERY_GROUP_IP, DISCOVERY_PORT)
ELECTION_PORT = 9002
HEARTBEAT_INTERVAL = 3.0
HEARTBEAT_TIMEOUT = 7.0
ELECTION_TIMEOUT = 5.0

# Globale Variablen für den Server-Zustand
my_ip = None
active_servers = []
connected_clients = []
current_leader = None
election_in_progress = False # Wichtig, um doppelte Wahlen zu vermeiden

# Nachrichtentypen für Server
class MessageType(enum.Enum):
    SERVER_DISCOVERY = 'SERVER_DISCOVERY'
    CLIENT_DISCOVERY = 'CLIENT_DISCOVERY'
    
    # Für Bully-Algorithmus
    ELECTION = 'ELECTION'
    ANSWER = 'ANSWER'
    COORDINATOR = 'COORDINATOR'

# Nachrichtentypen für den Chat
class ChatType(enum.Enum):
    CONNECT = 'CONNECT'
    MESSAGE = 'MESSAGE'
    DISCONNECT = 'DISCONNECT'

# Hilfsklassen zum Verpacken von Nachrichten
class DiscoveryMessage:
    def __init__(self, msg_type, server_list, client_list, leader_ip, client_name):
        self.msg_type = msg_type
        self.server_list = server_list
        self.client_list = client_list
        self.leader_ip = leader_ip
        self.client_name = client_name

class ChatMessage:
    def __init__(self, msg_type, username, content):
        self.msg_type = msg_type
        self.username = username
        self.content = content

class ElectionMessage:
    def __init__(self, msg_type, sender_ip):
        self.msg_type = msg_type
        self.sender_ip = sender_ip

# Hilfsfunktionen
def get_local_ip():
    # Findet die eigene IP-Adresse im Netzwerk
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def create_thread(target_function, args=()):
    # Erstellt einen neuen Thread und startet ihn
    thread = threading.Thread(target=target_function, args=args, daemon=True)
    thread.start()
    return thread

def deserialize_message(data):
    # Wandelt die empfangenen Bytes wieder in ein Objekt um
    try:
        return pickle.loads(data)
    except (pickle.UnpicklingError, EOFError):
        return None
