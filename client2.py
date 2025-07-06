import socket
import pickle
import os
import time
import threading
import common
# import discovery # Nicht mehr direkt für find_chat_leader benötigt

# Globale Variablen für den Client
username = ""
client_socket = None # Für Chat-Nachrichten
discovery_socket = None # Für Discovery-Nachrichten
is_connected = False

def initialize_client_sockets():
    global client_socket, discovery_socket
    if not client_socket:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if not discovery_socket:
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.settimeout(2.0) # Timeout für Discovery-Antworten

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

def find_chat_leader_locally(client_username):
    # Diese Funktion ist jetzt Teil von client.py
    global discovery_socket # Verwendet den client-eigenen Discovery-Socket

    if not discovery_socket: # Sollte durch initialize_client_sockets() bereits geschehen sein
        initialize_client_sockets()

    print(f"[CLIENT DISCOVERY] {client_username} sendet Discovery-Anfrage.")
    discovery_msg_obj = common.DiscoveryMessage(
        common.MessageType.CLIENT_DISCOVERY.value,
        [], [], None, client_username
    )
    payload = pickle.dumps(discovery_msg_obj)

    # An Multicast-Adresse senden
    try:
        discovery_socket.sendto(payload, common.DISCOVERY_ADDRESS)
    except Exception as e:
        print(f"[CLIENT DISCOVERY] Fehler beim Senden der Discovery-Nachricht: {e}")
        return False

    # Auf Antworten warten (mehrere Server könnten antworten)
    # Wir nehmen die erste gültige Antwort mit einer Leader-IP
    try:
        # Loop nicht notwendig, da recvfrom auf die erste Antwort wartet oder Timeout auslöst.
        # Wenn mehrere Server antworten, werden sie nacheinander vom Socket empfangen,
        # aber für die Leader-Findung reicht die erste gültige.
        data, addr = discovery_socket.recvfrom(1024)
        response = common.deserialize_message(data)
        if response and isinstance(response, common.DiscoveryMessage) and response.leader_ip:
            print(f"[CLIENT DISCOVERY] Antwort von {addr}: Leader ist {response.leader_ip}, Serverliste: {response.server_list}")
            common.current_leader = response.leader_ip
            common.active_servers = response.server_list # Client kennt nun aktive Server
            return True
        else:
            print(f"[CLIENT DISCOVERY] Ungültige oder irrelevante Antwort von {addr} empfangen.")
            return False
    except socket.timeout:
        print("[CLIENT DISCOVERY] Timeout bei der Suche nach dem Leader.")
        return False
    except Exception as e:
        print(f"[CLIENT DISCOVERY] Fehler beim Empfangen der Discovery-Antwort: {e}")
        return False

def connect_to_server():
    # Findet den Leader und stellt die Verbindung her.
    global is_connected, username # username hinzugefügt
    print("[CLIENT] Suche Server...")
    
    # Stellt sicher, dass die Sockets initialisiert sind
    initialize_client_sockets()

    # Verwende die lokale find_chat_leader_locally Funktion
    leader_found = find_chat_leader_locally(username)
    
    if leader_found and common.current_leader:
        print(f'[CLIENT] Leader gefunden: {common.current_leader}')
        leader_addr = (common.current_leader, common.CHAT_PORT)
        
        connect_msg_obj = common.ChatMessage(common.ChatType.CONNECT.value, username, 'ist jetzt online.')
        connect_msg = pickle.dumps(connect_msg_obj)

        try:
            # Sende über den Haupt-Chat-Socket
            client_socket.sendto(connect_msg, leader_addr)
            is_connected = True
            print("Verbunden! Du kannst jetzt chatten.\n> ", end="")
            return True
        except Exception as e:
            print(f"[CLIENT] Fehler beim Senden der Connect-Nachricht an Leader {common.current_leader}: {e}")
            common.current_leader = None # Leader scheint doch nicht erreichbar
            is_connected = False
            return False
    else:
        print("[CLIENT] Konnte keinen Leader finden.")
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
    global is_connected, client_socket, discovery_socket # discovery_socket hinzugefügt
    if is_connected:
        print(f"\n[CLIENT] {username} verlässt den Chat.")
        try:
            if common.current_leader: # common.current_leader könnte None sein
                leader_addr = (common.current_leader, common.CHAT_PORT)
                disconnect_msg_obj = common.ChatMessage(common.ChatType.DISCONNECT.value, username, 'ist jetzt offline.')
                disconnect_msg = pickle.dumps(disconnect_msg_obj)
                if client_socket: # Prüfen ob client_socket existiert
                    client_socket.sendto(disconnect_msg, leader_addr)
        except Exception:
            pass # Fehler beim Senden der Disconnect-Nachricht ignorieren
    
    is_connected = False
    if client_socket:
        client_socket.close()
        client_socket = None # Zurücksetzen, damit es neu erstellt werden kann
    if discovery_socket: # discovery_socket schließen
        discovery_socket.close()
        discovery_socket = None # Zurücksetzen
    os._exit(0)

def main():
    global username # client_socket wird in initialize_client_sockets() initialisiert
    
    try:
        username = input('Benutzername: ')
        # Sockets werden jetzt in initialize_client_sockets() erstellt,
        # das von connect_to_server() aufgerufen wird, welches vom connection_manager getriggert wird.
        # initialize_client_sockets() # Kann hier einmalig aufgerufen werden, um sicherzustellen.
        
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