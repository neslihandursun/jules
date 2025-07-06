import socket
import pickle
import os
import time
import threading
import common
import discovery

# Globale Variablen für den Client
username = ""
client_socket = None
is_connected = False

def send_chat_messages():
    # Kümmert sich um die Eingabe und das Senden von Nachrichten.
    global is_connected
    while True:
        try:
            user_input = input()
            if not is_connected:
                continue

            if user_input.lower() == '/quit':
                break
            
            message_obj = common.ChatMessage(common.ChatType.MESSAGE.value, username, user_input)
            message = pickle.dumps(message_obj)

            if common.current_leader:
                leader_addr = (common.current_leader, common.CHAT_PORT)
                client_socket.sendto(message, leader_addr)
            else:
                is_connected = False # Löst Reconnect aus

        except (EOFError, KeyboardInterrupt):
            break
        except Exception:
            is_connected = False

    shutdown_client()

def receive_chat_messages():
    # Empfängt Nachrichten vom Server.
    global is_connected
    while True:
        try:
            data, server_addr = client_socket.recvfrom(1024)
            if not data:
                raise ConnectionResetError

            try:
                msg = common.deserialize_message(data)
                if isinstance(msg, common.ChatMessage):
                     print(f"\r[{msg.username}] {msg.content}\n> ", end="")
                else:
                    print(f"\r{data.decode(common.ENCODING)}\n> ", end="")
            except:
                 print(f"\r{data.decode(common.ENCODING)}\n> ", end="")

        except (socket.timeout, ConnectionResetError):
            if is_connected:
                print("\n[CLIENT] Verbindung verloren. Versuche neu zu verbinden...")
                is_connected = False
        except Exception:
            if is_connected:
                 print("\n[CLIENT] Kritischer Fehler.")
            break

def connect_to_server():
    # Findet den Leader und stellt die Verbindung her.
    global is_connected
    print("[CLIENT] Suche Server...")
    
    leader_found = discovery.find_chat_leader(username)
    
    if leader_found and common.current_leader:
        print(f'[CLIENT] Leader gefunden: {common.current_leader}')
        leader_addr = (common.current_leader, common.CHAT_PORT)
        
        connect_msg_obj = common.ChatMessage(common.ChatType.CONNECT.value, username, 'ist jetzt online.')
        connect_msg = pickle.dumps(connect_msg_obj)
        client_socket.sendto(connect_msg, leader_addr)
        is_connected = True
        print("Verbunden! Du kannst jetzt chatten.\n> ", end="")
        return True
    else:
        is_connected = False
        return False

def connection_manager():
    # Ein Thread, der die Verbindung checkt und wiederherstellt.
    while True:
        if not is_connected:
            connect_to_server()
        time.sleep(5)

def shutdown_client():
    # Fährt den Client sauber herunter.
    global is_connected
    if is_connected:
        print(f"\n[CLIENT] {username} verlässt den Chat.")
        try:
            if common.current_leader:
                leader_addr = (common.current_leader, common.CHAT_PORT)
                disconnect_msg_obj = common.ChatMessage(common.ChatType.DISCONNECT.value, username, 'ist jetzt offline.')
                disconnect_msg = pickle.dumps(disconnect_msg_obj)
                client_socket.sendto(disconnect_msg, leader_addr)
        except Exception:
            pass
    
    is_connected = False
    if client_socket:
        client_socket.close()
    os._exit(0)

def main():
    global username, client_socket
    
    try:
        username = input('Benutzername: ')
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        common.create_thread(connection_manager)
        common.create_thread(receive_chat_messages)
        
        send_thread = threading.Thread(target=send_chat_messages)
        send_thread.start()
        send_thread.join()

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        shutdown_client()

if __name__ == '__main__':
    main()
