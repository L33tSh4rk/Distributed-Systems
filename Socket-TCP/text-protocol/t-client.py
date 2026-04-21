# cliente responsavel pela comunicação com servidor em protocolo de texto usando TCP
# Autor: Allan

import socket
import sys
import hashlib

def receive_line(sock, buffer):
    # extrai linha do buffer delimitada por \n
    while b'\n' not in buffer:
        chunk = sock.recv(1024)

        if not chunk:
            raise ConnectionAbortedError("connection closed by server")
        buffer += chunk
    
    linha, _, buffer = buffer.partition(b'\n')
    return linha.decode('utf-8'), buffer

def main():
    # configura socket do cliente
    host, port = '127.0.0.1', 65432
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

    except ConnectionRefusedError:
        print("[!] server offline or incorrect port")
        sys.exit(1)
        
    buffer = b""
    print("[!] connected to server via UTF protocol, type EXIT to quit.")


    try:
        while True: # fluxo de entrada cliente

            comando = input("UTFclient-server> ").strip()
            if not comando:
                continue

            # interceptacao e hashing
            if comando.startswith("CONNECT "):
                payload = comando[8:]
                partes = payload.split(",", 1)
                
                if len(partes) == 2:
                    usuario = partes[0].strip()
                    senha_plana = partes[1].strip()
                    
                    # transforma senha para hash sha-512
                    hash_senha = hashlib.sha512(senha_plana.encode('utf-8')).hexdigest()
                    
                    # remonta comando formatado para servidor
                    comando_rede = f"CONNECT {usuario}, {hash_senha}"
                else:
                    # envia malformado de proposito para server barrar
                    comando_rede = comando
            else:
                comando_rede = comando
                
            # empacota e despacha comando
            sock.sendall((comando_rede + "\n").encode('utf-8'))


            # roteamento de leitura da resposta
            if comando == "GETFILES" or comando == "GETDIRS":
                try:
                    # le tamanho do lote
                    qtd_str, buffer = receive_line(sock, buffer)
                    
                    if qtd_str in ["ERROR", "ERROR_NOT_IMPLEMENTED"]:
                        print(f"server: {qtd_str}")
                        continue
                        
                    qtd = int(qtd_str)
                    print(f"[{qtd} items found]:")
                    
                    # laço de consumo
                    for _ in range(qtd):
                        item, buffer = receive_line(sock, buffer)
                        print(f"  - {item}")
                        
                except ValueError:
                    print(f"[!] protocol error: malformed quantity -> {qtd_str}")
                    

            elif comando == "EXIT":
                # aguarda confirmacao de desligamento
                resposta, buffer = receive_line(sock, buffer)
                print(f"server: {resposta}")
                break
                

            else:
                # leitura padrao para respostas simples
                resposta, buffer = receive_line(sock, buffer)
                print(f"server: {resposta}")



    except ConnectionAbortedError as e:
        print(f"\n[!] {e}")
    except KeyboardInterrupt:
        print("\n[!] terminal interruption")
    finally:
        sock.close()


if __name__ == "__main__":
    main()