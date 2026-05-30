# codigo responsavel pelo servidor de gerenciamento de uploads que utiliza de protocolo UDP, funcional por meio de lote/bitmap para transferência de arquivos
# Autor: Allan

import socket
import struct
import hashlib
import math
from pathlib import Path

# constantes de protocolo
TIPO_META = 1
TIPO_DATA = 2
TIPO_END = 3
TIPO_NACK = 4
TIPO_SUCCESS = 5
TIPO_FAIL = 6

CHUNK_SIZE = 1024
PASTA_PADRAO = Path("server_uploads")
PASTA_PADRAO.mkdir(exist_ok=True)

def calcular_sha1(caminho_arquivo):
    sha1 = hashlib.sha1()
    with open(caminho_arquivo, 'rb') as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.digest()

def main():
    host, port = '0.0.0.0', 65432
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    
    print(f"[*] p2p UDP server (batch/bitmap) listening on port {port}")
    
    # variaveis de sessao
    arquivo_atual = None
    tamanho_total = 0
    total_chunks = 0
    chunks_recebidos = set()
    caminho_arquivo = None

    try:
        while True:
            pacote, addr = sock.recvfrom(2048) # buffer maior que 1024 pra caber o cabecalho
            tipo = pacote[0]

            if tipo == TIPO_META:
                # desempacota tamanho do arquivo e do nome
                tamanho_total, tam_nome = struct.unpack('!QH', pacote[1:11])
                nome_arquivo = pacote[11 : 11 + tam_nome].decode('utf-8')

                total_chunks = math.ceil(tamanho_total / CHUNK_SIZE)
                chunks_recebidos.clear()

                caminho_arquivo = PASTA_PADRAO / nome_arquivo
                print(f"\n[*] receiving {nome_arquivo} ({tamanho_total} bytes, {total_chunks} chunks)")

                # cria o arquivo vazio
                with open(caminho_arquivo, 'wb') as f:
                    pass

            elif tipo == TIPO_DATA:
                if not caminho_arquivo: continue # ignora lixo antes do META

                # desempacota Sequence Number e Dados Brutos
                seq_num = struct.unpack('!I', pacote[1:5])[0]
                dados = pacote[5:]

                # grava em disco usando o offset (SeqNum * 1024)
                with open(caminho_arquivo, 'r+b') as f:
                    f.seek(seq_num * CHUNK_SIZE)
                    f.write(dados)

                chunks_recebidos.add(seq_num)

            elif tipo == TIPO_END:
                if not caminho_arquivo: continue

                sha1_cliente = pacote[1:21]
                faltando = set(range(total_chunks)) - chunks_recebidos

                if not faltando:
                    # todos os blocos chegaram. valida SHA-1.
                    print("[*] all blocks received. validating integrity...")
                    sha1_servidor = calcular_sha1(caminho_arquivo)

                    if sha1_cliente == sha1_servidor:
                        print("[+] 100% integrity validated. success.")
                        sock.sendto(struct.pack('!B', TIPO_SUCCESS), addr)
                    else:
                        print("[-] integrity failure. SHA-1 does not match.")
                        sock.sendto(struct.pack('!B', TIPO_FAIL), addr)

                    # reseta sessao
                    caminho_arquivo = None 

                else:
                    # bitmap: faltam pedacos. avisa cliente.
                    lista_faltando = list(faltando)
                    # limita 250 chunks perdidos por pacote de NACK para nao estourar limite de rede
                    lote = lista_faltando[:250] 
                    print(f"[!] {len(lista_faltando)} packets missing.")

                    # empacota
                    formato_nack = f'!BH{len(lote)}I'
                    pacote_nack = struct.pack(formato_nack, TIPO_NACK, len(lote), *lote)
                    sock.sendto(pacote_nack, addr)
    except KeyboardInterrupt:
        print("\n[!] server shut down (SIGINT).")
    finally:
        sock.close()


if __name__ == "__main__":
    main()