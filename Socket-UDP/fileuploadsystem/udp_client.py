# código responsável pelo cliente que interage com o servidor UDP, enviando arquivos para ele por meio da rede
# Autor: Allan

import socket
import struct
import hashlib
import math
import sys
import time
from pathlib import Path
import random

TIPO_META = 1
TIPO_DATA = 2
TIPO_END = 3
TIPO_NACK = 4
TIPO_SUCCESS = 5
TIPO_FAIL = 6

CHUNK_SIZE = 1024

def enviar_chunk(sock, addr, f, seq_num):
    # vai ate disco le pedaco exato e faz envio do pacote
    f.seek(seq_num * CHUNK_SIZE)
    dados = f.read(CHUNK_SIZE)
    pacote = struct.pack(f'!BI{len(dados)}s', TIPO_DATA, seq_num, dados)
    sock.sendto(pacote, addr)

def main():
    if len(sys.argv) < 2:
        print("usage: python3 udp_client.py <file_path>\ninfo: use absolute path to transfer the correct file.")
        return

    caminho = Path(sys.argv[1]).resolve()
    if not caminho.is_file():
        print(f"file not found: {caminho}")
        return

    host_destino, port_destino = '127.0.0.1', 65432
    addr = (host_destino, port_destino)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0) # timeout crucial para UDP
    
    # ler metadados e calcular SHA-1
    print("[*] calculating file SHA-1...")
    sha1_hash = hashlib.sha1()
    tamanho_total = caminho.stat().st_size
    total_chunks = math.ceil(tamanho_total / CHUNK_SIZE)
    
    with open(caminho, 'rb') as f:
        while chunk := f.read(8192):
            sha1_hash.update(chunk)
    digest_final = sha1_hash.digest()

    # enviar primeiro pacote (META)
    nome_bytes = caminho.name.encode('utf-8')
    pacote_meta = struct.pack(f'!BQH{len(nome_bytes)}s', TIPO_META, tamanho_total, len(nome_bytes), nome_bytes)
    sock.sendto(pacote_meta, addr)
    
    print(f"[*] starting file transfer: {total_chunks} packets...")
    
    with open(caminho, 'rb') as f:
        # fire-and-forget
        for seq_num in range(total_chunks):
            if random.random() < 0.05:          # simulando perda de pacotes na rede para usar NACK
                enviar_chunk(sock, addr, f, seq_num)
            
            # pausa se estourar buffer da placa de rede local
            time.sleep(0.0001)
            
        # checksum final e entrada no laco de sincronizacao
        pacote_end = struct.pack('!B20s', TIPO_END, digest_final)
        sock.sendto(pacote_end, addr)
        
        while True:
            try:
                resposta, _ = sock.recvfrom(2048)
                tipo = resposta[0]
                
                if tipo == TIPO_SUCCESS:
                    print("[+] server confirmed. transfer 100% integrity.")
                    break
                    
                elif tipo == TIPO_FAIL:
                    print("[-] server rejected file. irreversibly corrupted file.")
                    break
                    
                elif tipo == TIPO_NACK:
                    # desempacota qtd de pacotes faltando e lista de SeqNums
                    qtd = struct.unpack('!H', resposta[1:3])[0]
                    faltando = struct.unpack(f'!{qtd}I', resposta[3 : 3 + (qtd * 4)])
                    
                    print(f"[!] server requested recovery of {qtd} lost packets. resending...")
                    for seq in faltando:
                        enviar_chunk(sock, addr, f, seq)
                        
                    # avisa servidor que terminamos resgate
                    sock.sendto(pacote_end, addr)
                    
            except socket.timeout:
                # opacote END do cliente ou SUCCESS do servidor se perdeu
                print("[-] timeout. server did not respond. resending final packet (END)...")
                sock.sendto(pacote_end, addr)

    sock.close()

if __name__ == "__main__":
    main()