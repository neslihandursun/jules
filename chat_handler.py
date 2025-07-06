import socket
import pickle
import common

chat_socket = None

def start_chat_server():
    # Startet den Server, der auf Chat-Nachrichten lauscht.
    global chat_socket
    chat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    chat_socket.bind(('', common.CHAT_PORT))
    print(f'[CHAT] Server lauscht auf Port {common.CHAT_PORT}')

    while True:
        try:
            data, client_addr = chat_socket.recvfrom(1024)
            
            # Nur der Leader verarbeitet Nachrichten direkt.
            if common.current_leader == common.my_ip:
                process_leader_tasks(data, client_addr)
            else:
                # Andere Server leiten die Anfrage an den Leader weiter.
                if common.current_leader:
                    leader_addr = (common.current_leader, common.CHAT_PORT)
                    chat_socket.sendto(data, leader_addr)

        except Exception as e:
            print(f'[CHAT] Fehler: {e}')

def process_leader_tasks(data, client_addr):
    # Logik, die nur der Leader ausführt.
    message = common.deserialize_message(data)
    if not message or not isinstance(message, common.ChatMessage):
        return

    # Neuer Client verbindet sich.
    if message.msg_type == common.ChatType.CONNECT.value:
        if client_addr not in common.connected_clients:
            common.connected_clients.append(client_addr)
            print(f"[CHAT] Client {message.username}@{client_addr} verbunden.")
            broadcast_message(f"--- {message.username} ist dem Chat beigetreten. ---", None)

    # Client sendet eine Nachricht.
    elif message.msg_type == common.ChatType.MESSAGE.value:
        print(f"[{message.username}] {message.content}")
        broadcast_message(message, client_addr)

    # Client verlässt den Chat.
    elif message.msg_type == common.ChatType.DISCONNECT.value:
        if client_addr in common.connected_clients:
            common.connected_clients.remove(client_addr)
            print(f"[CHAT] Client {message.username}@{client_addr} hat die Verbindung getrennt.")
            broadcast_message(f"--- {message.username} hat den Chat verlassen. ---", None)

def broadcast_message(message_obj, sender_addr):
    # Sendet eine Nachricht an alle verbundenen Clients.
    
    # Wenn es nur ein String ist (Server-Nachricht)
    if isinstance(message_obj, str):
        payload = pickle.dumps(common.ChatMessage(common.ChatType.MESSAGE.value, "SERVER", message_obj))
    # Wenn es ein ChatMessage-Objekt ist
    else:
        payload = pickle.dumps(message_obj)

    # Sende an alle Clients in der Liste.
    for client in list(common.connected_clients):
        # Sende nicht an den Absender zurück, außer bei Server-Nachrichten
        if sender_addr is None or client != sender_addr:
            try:
                chat_socket.sendto(payload, client)
            except Exception:
                # Wenn Senden fehlschlägt, Client entfernen.
                print(f"[CHAT] Client {client} nicht erreichbar, wird entfernt.")
                common.connected_clients.remove(client)
