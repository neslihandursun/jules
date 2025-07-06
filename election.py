import socket
import pickle
import time
import threading
import common

# Kümmert sich um Leader-Wahl nach dem Bully-Algorithmus.
class BullyElection:
    def __init__(self, my_ip):
        self.my_ip = my_ip
        self.election_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.election_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.election_socket.bind(('', common.ELECTION_PORT))
        self.election_timer = None
        print(f"[ELECTION] Listener bereit auf Port {common.ELECTION_PORT}")

    def start_election_thread(self):
        # Startet einen Thread, der auf Wahlnachrichten wartet.
        common.create_thread(self.listen_for_election_messages)

    def listen_for_election_messages(self):
        # im Hintergrund auf Nachrichten.
        while True:
            try:
                data, addr = self.election_socket.recvfrom(1024)
                message = common.deserialize_message(data)
                if message:
                    self.process_election_message(message, addr)
            except Exception as e:
                print(f"[ELECTION] Fehler beim Empfang: {e}")

    def start_election(self):
        # Tritt eine Wahl los.
        if common.election_in_progress:
            return

        print(f"[ELECTION] {self.my_ip} startet eine Wahl.")
        common.election_in_progress = True
        
        # Finde alle Server mit einer höheren IP.
        higher_servers = [s_ip for s_ip in common.active_servers if s_ip > self.my_ip]

        if not higher_servers:
            # Keine höheren Server gefunden? Dann bin ich der neue Leader.
            self.become_leader()
            return

        # Schicke "ELECTION" an alle höheren Server.
        election_msg = common.ElectionMessage(common.MessageType.ELECTION, self.my_ip)
        payload = pickle.dumps(election_msg)
        for server_ip in higher_servers:
            self.election_socket.sendto(payload, (server_ip, common.ELECTION_PORT))

        # Starte einen Timer. Wenn niemand antwortet, gewinne ich.
        if self.election_timer:
            self.election_timer.cancel()
        self.election_timer = threading.Timer(common.ELECTION_TIMEOUT, self.handle_election_timeout)
        self.election_timer.start()

    def process_election_message(self, message, addr):
        # Verarbeitet die verschiedenen Wahlnachrichten.
        sender_ip = addr[0]

        if message.msg_type == common.MessageType.ELECTION:
            # Ein Server mit niedrigerer IP hat eine Wahl gestartet.
            # Schicke ihm eine "ANSWER", um zu zeigen, dass es mich gibt.
            answer_msg = common.ElectionMessage(common.MessageType.ANSWER, self.my_ip)
            payload = pickle.dumps(answer_msg)
            self.election_socket.sendto(payload, (sender_ip, common.ELECTION_PORT))
            
            # Starte selbst eine Wahl, falls noch nicht geschehen.
            if not common.election_in_progress:
                self.start_election()

        elif message.msg_type == common.MessageType.ANSWER:
            # Ein höherer Server hat geantwortet. Ich habe verloren.
            # Breche meinen Wahl-Timer ab.
            if self.election_timer:
                self.election_timer.cancel()
            common.election_in_progress = False

        elif message.msg_type == common.MessageType.COORDINATOR:
            # Ein neuer Leader wurde gewählt.
            new_leader_ip = message.sender_ip
            print(f"[ELECTION] Neuer Leader ist {new_leader_ip}.")
            common.current_leader = new_leader_ip
            if self.election_timer:
                self.election_timer.cancel()
            common.election_in_progress = False

    def handle_election_timeout(self):
        # Mein Timer ist abgelaufen, kein höherer Server hat geantwortet.
        if common.election_in_progress:
            self.become_leader()

    def become_leader(self):
        # Ich bin der neue Leader.
        common.current_leader = self.my_ip
        common.election_in_progress = False
        if self.election_timer:
            self.election_timer.cancel()

        print(f"[LEADER] Ich ({self.my_ip}) bin der neue Leader.")
        
        # Schicke eine "COORDINATOR" Nachricht an alle anderen, damit sie es wissen.
        coordinator_msg = common.ElectionMessage(common.MessageType.COORDINATOR, self.my_ip)
        payload = pickle.dumps(coordinator_msg)

        other_servers = [s_ip for s_ip in common.active_servers if s_ip != self.my_ip]
        for server_ip in other_servers:
            try:
                self.election_socket.sendto(payload, (server_ip, common.ELECTION_PORT))
            except Exception as e:
                print(f"[LEADER] Fehler beim Senden der Coordinator-Nachricht an {server_ip}: {e}")
