# cliente responsavel pela comunicação com servidor em protocolo Binario usando TCP
# Autor: Allan

import socket
import struct
import sys
from pathlib import Path
import os

# constantes do protocolo
MSG_REQ = 0x01
MSG_RES = 0x02

CMD_ADDFILE = 0x01
CMD_DELETE = 0x02
CMD_GETFILESLIST = 0x03
CMD_GETFILE = 0x04

STATUS_SUCCESS = 0x01
STATUS_ERROR = 0x02


# define pasta de download local do cliente
pasta_cliente = Path.cwd() / "client_downloads"
pasta_cliente.mkdir(exist_ok=True)


def recv_exact(sock, n):
    # le n bytes do socket
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            raise ConnectionAbortedError("connection dropped during read")
        data.extend(packet)
    return data


def ler_cabecalho_resposta(sock):
    # extrai e valida 3 bytes padroes de resposta
    cabecalho = recv_exact(sock, 3)
    msg_type, cmd_id, status = struct.unpack('!BBB', cabecalho)
    
    if msg_type != MSG_RES:
        print("[!] ERROR : malformed response from server.")
        return False, cmd_id
        
    return status == STATUS_SUCCESS, cmd_id


def main():
    # inicializa socket bloqueante padrao
    host, port = '127.0.0.1', 65432
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("[!] connected to the binary server. Type EXIT to close.")
    except ConnectionRefusedError:
        print("[!] server offline.")
        sys.exit(1)

    try:
        while True: # fluxo de entrada cliente
            try:
                entrada = input("\nBINclient-server> ").strip().split()

            except UnicodeDecodeError:
                print("[!] warning: invisible character or invalid accent detected in terminal. Please type again.")
                continue

            if not entrada:
                continue
                
            comando = entrada[0].upper()

            if comando == "EXIT":
                break
            
            elif comando == "HELP":
                # execução local para cliente saber comandos aceitos
                print("[*] accepted commands: ADDFILE | DELETE | GETFILESLIST | GETFILE | EXIT | HELP")
                continue

            elif comando == "DELETE":
                if len(entrada) < 2:
                    print("usage: DELETE <filename>")
                    continue
                nome_arq = entrada[1]
                nome_bytes = nome_arq.encode('utf-8')
                
                # empacota tipo, cmd_id e tamanho do nome
                pacote = struct.pack('!BBB', MSG_REQ, CMD_DELETE, len(nome_bytes)) + nome_bytes
                sock.sendall(pacote)
                
                # aguarda confirmacao
                sucesso, _ = ler_cabecalho_resposta(sock)
                if sucesso:
                    print(f"[*] file {nome_arq} deleted successfully.")
                else:
                    print(f"[!] failed to delete {nome_arq}.")


            elif comando == "GETFILESLIST":
                # tamanho do nome zerado pra listagem geral
                pacote = struct.pack('!BBB', MSG_REQ, CMD_GETFILESLIST, 0)
                sock.sendall(pacote)
                
                sucesso, _ = ler_cabecalho_resposta(sock)


                if sucesso:
                    # extrai 2 bytes da qtd total
                    qtd_bytes = recv_exact(sock, 2)
                    qtd = struct.unpack('!H', qtd_bytes)[0]
                    print(f"[*] {qtd} files found:")
                    
                    # leitura nome a nome
                    for _ in range(qtd):
                        tam_nome = struct.unpack('!B', recv_exact(sock, 1))[0]
                        nome = recv_exact(sock, tam_nome).decode('utf-8')
                        print(f"  - {nome}")
                else:
                    print("[!] failed to list directory.")


            elif comando == "GETFILE":
                if len(entrada) < 2:
                    print("usage: GETFILE <filename>")
                    continue

                nome_arq = entrada[1]
                nome_bytes = nome_arq.encode('utf-8')
                
                pacote = struct.pack('!BBB', MSG_REQ, CMD_GETFILE, len(nome_bytes)) + nome_bytes
                sock.sendall(pacote)
                
                sucesso, _ = ler_cabecalho_resposta(sock)

                if sucesso:
                    # extrai 4 bytes do tamanho do arquivo
                    tam_arq_bytes = recv_exact(sock, 4)
                    tam_arq = struct.unpack('!I', tam_arq_bytes)[0]
                    
                    caminho_salvar = pasta_cliente / nome_arq
                    recebidos = 0
                    
                    # inicia streaming de disco do cliente
                    print(f"[*] downloading {nome_arq} ({tam_arq} bytes)...")
                    with open(caminho_salvar, 'wb') as f:
                        while recebidos < tam_arq:
                            falta = tam_arq - recebidos
                            # ajusta buffer para nao ler a mais e engolir proximo cabecalho
                            chunk_size = min(4096, falta) 
                            chunk = sock.recv(chunk_size)
                            if not chunk:
                                raise ConnectionAbortedError("connection dropped during download.")
                            f.write(chunk)
                            recebidos += len(chunk)
                            
                    print(f"[*] download completed at {caminho_salvar}")
                else:
                    print(f"[!] failure: file {nome_arq} does not exist or permission denied.")


            elif comando == "ADDFILE":
                if len(entrada) < 2:
                    print("usage: ADDFILE <local_file_path>")
                    continue
                
                caminho_local = Path(entrada[1]).resolve()

                if not caminho_local.is_file():
                    print(f"[!] local file not found: {caminho_local}")
                    continue
                    
                nome_arq = caminho_local.name
                nome_bytes = nome_arq.encode('utf-8')
                tam_arq = caminho_local.stat().st_size
                
                # empacota cabecalho + nome + 4 bytes do tamanho
                cabecalho = struct.pack('!BBB', MSG_REQ, CMD_ADDFILE, len(nome_bytes)) + nome_bytes
                tamanho_bytes = struct.pack('!I', tam_arq)
                sock.sendall(cabecalho + tamanho_bytes)
                
                # inicia streaming de upload
                print(f"[*] sending {nome_arq} ({tam_arq} bytes)...")
                with open(caminho_local, 'rb') as f:
                    while chunk := f.read(4096):
                        sock.sendall(chunk)
                        
                sucesso, _ = ler_cabecalho_resposta(sock)

                if sucesso:
                    print(f"[*] upload completed.")
                else:
                    print(f"[!] server failed to receive file.")

            else:
                print(f"[!] unknown command: {comando}. Use HELP.")



    except ConnectionAbortedError as e:
        print(f"\n[!] {e}")
    except KeyboardInterrupt:
        print("\n[!] terminal closed.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()