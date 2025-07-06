import sys
import time
import common
import chat_handler
import discovery
from election import BullyElection
import heartbeat

def display_network_status():
    # Zeigt Infos zum aktuellen Zustand des Netzwerks.
    leader_status = common.current_leader if common.current_leader else "Unbekannt"
    print(f"\n--- Status ---")
    print(f"  Meine IP: {common.my_ip}")
    print(f"  Server: {common.active_servers}")
    print(f"  Leader: {leader_status}")
    print(f"  Clients: {len(common.connected_clients)}")
    print(f"----------------\n")

def main():
    common.my_ip = common.get_local_ip()
    print(f'[SERVER] Starte Server, IP: {common.my_ip}')

    # Wahl-Manager initialisieren
    election_manager = BullyElection(common.my_ip)
    election_manager.start_election_thread()

    # Andere Dienste im Hintergrund starten
    discovery.initialize_discovery_receiver()
    common.create_thread(chat_handler.start_chat_server)
    common.create_thread(discovery.handle_discovery_messages)
    heartbeat.start_heartbeat(election_manager)

    # Sich selbst im Netzwerk bekannt machen
    time.sleep(1)
    if common.my_ip not in common.active_servers:
        common.active_servers.append(common.my_ip)
    
    discovery.announce_server_presence()
    
    time.sleep(2) # Auf Antworten von anderen warten

    # Wenn nach dem Start kein Leader da ist, Wahl starten
    if not common.current_leader:
        print("[SERVER] Kein Leader da, starte erste Wahl.")
        election_manager.start_election()

    # Hauptschleife
    last_display_time = time.time()
    while True:
        try:
            # Status alle 15s anzeigen
            if time.time() - last_display_time > 15:
                display_network_status()
                last_display_time = time.time()
            
            time.sleep(1)

        except KeyboardInterrupt:
            print(f'\n[SERVER] Server wird beendet.')
            sys.exit(0)

if __name__ == '__main__':
    main()
