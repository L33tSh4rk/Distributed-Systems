# codigo responsavel pelo segundo nó de cliente no chat p2p
# Autor: Allan

import socket
import struct
import threading
import sys
import readline

# limites de protocolo
MAX_NICK_SIZE = 64
MAX_MSG_SIZE = 255

# tipos de mensagem
TIPO_NORMAL = 1
TIPO_EMOJI = 2
TIPO_URL = 3
TIPO_ECHO = 4

def empacotar_mensagem(tipo, apelido, mensagem):
    # converte strings para bytes utf-8
    apelido_bytes = apelido.encode('utf-8')
    msg_bytes = mensagem.encode('utf-8')
    
    # garante limites impostos pelo protocolo
    if len(apelido_bytes) > MAX_NICK_SIZE:
        apelido_bytes = apelido_bytes[:MAX_NICK_SIZE]
    if len(msg_bytes) > MAX_MSG_SIZE:
        msg_bytes = msg_bytes[:MAX_MSG_SIZE]
        
    tam_apl = len(apelido_bytes)
    tam_msg = len(msg_bytes)
    
    # formato: ! (big-endian), B (1 byte tipo), B (1 byte tam_apl), 
    # [tam_apl]s (bytes do apelido), B (1 byte tam_msg), [tam_msg]s (bytes da msg)
    formato = f'!BB{tam_apl}sB{tam_msg}s'
    
    # cria datagrama binario
    pacote = struct.pack(formato, tipo, tam_apl, apelido_bytes, tam_msg, msg_bytes)
    return pacote

def desempacotar_mensagem(pacote):
    try:
        # extrai dois primeiros bytes (tipo e tamanho do apelido)
        tipo, tam_apl = struct.unpack('!BB', pacote[:2])
        
        # extrai apelido fatiando bytes
        apelido_bytes = pacote[2 : 2 + tam_apl]
        apelido = apelido_bytes.decode('utf-8')
        
        # proximo byte apos apelido e tamanho da mensagem
        idx_tam_msg = 2 + tam_apl
        tam_msg = struct.unpack('!B', pacote[idx_tam_msg : idx_tam_msg + 1])[0]
        
        # restante dos bytes é mensagem
        msg_bytes = pacote[idx_tam_msg + 1 : idx_tam_msg + 1 + tam_msg]
        mensagem = msg_bytes.decode('utf-8')
        
        return tipo, apelido, mensagem
    except Exception as e:
        return None, None, None

def thread_recepcao(sock):
    # daemon thread que escuta rede
    while True:
        try:
            pacote, addr = sock.recvfrom(1024)
            tipo, apelido, mensagem = desempacotar_mensagem(pacote)
            
            if tipo is None:
                continue
                
            # captura o que usuario digitou ate momento (sem enviar)
            texto_pendente = readline.get_line_buffer()
            
            # volta cursor pro inicio + apaga linha atual
            sys.stdout.write('\r\033[2K')
            
            # formatação visual baseada no tipo de mensagem
            if tipo == TIPO_NORMAL:
                print(f"[{apelido}]: {mensagem}")
            elif tipo == TIPO_EMOJI:
                print(f"[{apelido} sent an EMOJI]: {mensagem}")
            elif tipo == TIPO_URL:
                print(f"[{apelido} shared a URL]: {mensagem}")
            elif tipo == TIPO_ECHO:
                print(f"[ECHO of {apelido}]: {mensagem} (active user)")
            
            # redesenha prompt e devolve texto pendente pra usuario continuar digitando
            sys.stdout.write(f"p2p> {texto_pendente}")
            sys.stdout.flush()
                
        except OSError:
            break # fecha socket

def main():
    print("=== UDP P2P CHAT ===")
    apelido = input("enter your nickname: ").strip()
    porta_local = int(input("enter local port to listen on (e.g.: 5002): "))
    
    ip_destino = input("enter destination IP (e.g.: 127.0.0.1): ").strip()
    porta_destino = int(input("enter destination port (e.g.: 5001): "))
    
    # cria socket udp
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', porta_local))
    
    print(f"\n[!] node online. listening on port {porta_local}.")
    print("[!] commands: type normally or start with !emoji, !url, !echo to change type.")
    
    # inicia thread de recepcao em background
    rx_thread = threading.Thread(target=thread_recepcao, args=(sock,), daemon=True)
    rx_thread.start()
    
    try:
        # loop de thread principal (transmissão)
        while True:
            entrada = input("p2p> ").strip()
            if not entrada:
                continue
                
            # roteador logico de tipo de mensagem
            if entrada.startswith("!emoji "):
                tipo = TIPO_EMOJI
                mensagem = entrada[7:]
            elif entrada.startswith("!url "):
                tipo = TIPO_URL
                mensagem = entrada[5:]
            elif entrada.startswith("!echo "):
                tipo = TIPO_ECHO
                mensagem = entrada[6:]
            elif entrada.lower() == "exit":
                break
            else:
                tipo = TIPO_NORMAL
                mensagem = entrada
                
            # empacota e envia pacote na rede (sem conexao prévia)
            pacote = empacotar_mensagem(tipo, apelido, mensagem)
            sock.sendto(pacote, (ip_destino, porta_destino))
            
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[!] shutting down p2p node...")
        sock.close()
        sys.exit(0)

if __name__ == "__main__":
    main()