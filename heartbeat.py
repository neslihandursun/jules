import socket
import time
import pickle
import sys
import common

def start_heartbeat(election_manager):
    # Startet den Heartbeat-Thread.
    common.create_thread(monitor_leader_health, args=(election_manager,))

def monitor_leader_health(election_manager):
    # Wartet kurz nach dem Serverstart.
    time.sleep(5) 
    
    while True:
        # Nur Nicht-Leader-Server prüfen den Leader.
        if common.current_leader and common.current_leader != common.my_ip:
            target_leader = common.current_leader
            
            ping_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ping_socket.settimeout(common.HEARTBEAT_TIMEOUT)
            
            try:
                # Sende einen einfachen Ping an den Chat-Port des Leaders.
                ping_socket.sendto(b'PING', (target_leader, common.CHAT_PORT))
                # Wir warten hier nicht auf eine Antwort, ein Fehler beim Senden reicht als Indikator.
                
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                # Der Leader antwortet nicht.
                print(f"[HEARTBEAT] Leader {target_leader} scheint down zu sein! ({e})", file=sys.stderr)
                
                # Sicherstellen, dass sich der Leader nicht inzwischen geändert hat.
                if common.current_leader == target_leader:
                    common.current_leader = None
                    if target_leader in common.active_servers:
                        common.active_servers.remove(target_leader)
                    
                    # Starte eine Neuwahl.
                    election_manager.start_election()
            
            finally:
                ping_socket.close()

        # Warte für das nächste Intervall.
        time.sleep(common.HEARTBEAT_INTERVAL)
