import socket
import struct
import pickle
import time
import common

# Sockets für das Senden und Empfangen von Multicast-Nachrichten
sender_socket = None
receiver_socket = None

def initialize_discovery_receiver():
    # Bereitet den Socket vor, um Multicast-Nachrichten zu empfangen.
    global receiver_socket
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    receiver_socket.bind(('', common.DISCOVERY_PORT))

    # Tritt der Multicast-Gruppe bei.
    group = socket.inet_aton(common.DISCOVERY_GROUP_IP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    receiver_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    print(f"[DISCOVERY] Listener bereit auf {common.DISCOVERY_ADDRESS}")

def announce_server_presence():
    # Ein Server macht sich im Netzwerk bemerkbar.
    global sender_socket
    if not sender_socket:
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender_socket.settimeout(0.5)

    # Nachricht mit den aktuellen Server-Infos.
    discovery_msg = common.DiscoveryMessage(
        common.MessageType.SERVER_DISCOVERY.value,
        common.active_servers,
        common.connected_clients,
        common.current_leader,
        ''
    )
    payload = pickle.dumps(discovery_msg)
    sender_socket.sendto(payload, common.DISCOVERY_ADDRESS)

# Die Funktion find_chat_leader wurde nach client.py verschoben und dort als
# find_chat_leader_locally implementiert, da sie spezifisch für den Client ist
# und dessen eigenen Discovery-Socket verwendet.
# def find_chat_leader(username):
# # Ein Client sucht nach dem Leader.
# global sender_socket
# if not sender_socket:
# sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sender_socket.settimeout(2.0)
#
# discovery_msg = common.DiscoveryMessage(
# common.MessageType.CLIENT_DISCOVERY.value,
#         [], [], None, username
# )
#     payload = pickle.dumps(discovery_msg)
# sender_socket.sendto(payload, common.DISCOVERY_ADDRESS)
#
# try:
# # Warte auf eine Antwort vom Leader.
#         data, addr = sender_socket.recvfrom(1024)
#         response = common.deserialize_message(data)
#         if response and isinstance(response, common.DiscoveryMessage):
# # Speichere die erhaltenen Infos.
# common.current_leader = response.leader_ip
# common.active_servers = response.server_list
# return True
# except socket.timeout:
# return False

def handle_discovery_messages():
    # Verarbeitet alle eingehenden Discovery-Nachrichten.
    while True:
        try:
            data, addr = receiver_socket.recvfrom(1024)
            message = common.deserialize_message(data)
            if not message:
                continue

            # Ein anderer Server meldet sich.
            if message.msg_type == common.MessageType.SERVER_DISCOVERY.value:
                sender_ip = addr[0]
                if sender_ip not in common.active_servers:
                    common.active_servers.append(sender_ip)
                    print(f"[DISCOVERY] Neuer Server gefunden: {sender_ip}")

                # Wenn ich der Leader bin, antworte ich mit meinem Zustand.
                if common.current_leader == common.my_ip:
                    response_msg = common.DiscoveryMessage(
                        common.MessageType.SERVER_DISCOVERY.value,
                        common.active_servers,
                        common.connected_clients,
                        common.current_leader,
                        ''
                    )
                    payload = pickle.dumps(response_msg)
                    receiver_socket.sendto(payload, addr)

            # Ein Client sucht den Leader.
            elif message.msg_type == common.MessageType.CLIENT_DISCOVERY.value:
                print(f"[DISCOVERY] Client '{message.client_name}' (von {addr}) sucht den Leader.")
                # Jeder Server, der den Leader kennt, kann antworten.
                # Dies hilft dem Client, schneller Informationen zu bekommen,
                # insbesondere nach einem Leader-Failover.
                if common.current_leader: # Wenn ein Leader bekannt ist (egal ob ich es bin oder ein anderer)
                    response_msg = common.DiscoveryMessage(
                        common.MessageType.SERVER_DISCOVERY.value,
                        common.active_servers, # Schicke die aktuelle Liste der aktiven Server
                        [], # Client-Liste ist nur für den Leader relevant (und wird hier nicht benötigt)
                        common.current_leader, # Schicke den bekannten Leader
                        ''
                    )
                    payload = pickle.dumps(response_msg)

                    # Sicherstellen, dass der sender_socket initialisiert ist
                    # Der globale sender_socket wird hier wiederverwendet
                    global sender_socket
                    if not sender_socket:
                        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        # Da dies im Empfangsthread läuft, sollte der Timeout nicht blockieren.
                        # Ein kurzer Timeout oder nicht-blockierendes Senden wäre ideal,
                        # aber für UDP ist sendto normalerweise nicht blockierend.
                        # sender_socket.settimeout(0.2) # Kurzer Timeout für Sendeversuche (optional)

                    sender_socket.sendto(payload, addr) # Sende an die Adresse, von der die Anfrage kam

                    if common.my_ip == common.current_leader:
                        print(f"[DISCOVERY] Ich bin Leader, habe Client {message.client_name} geantwortet.")
                    else:
                        print(f"[DISCOVERY] Kenne Leader {common.current_leader}, habe Client {message.client_name} geantwortet.")
                else:
                    print(f"[DISCOVERY] Kenne aktuell keinen Leader, antworte nicht auf Client {message.client_name}.")

        except Exception as e:
            print(f"[DISCOVERY] Fehler: {e}")