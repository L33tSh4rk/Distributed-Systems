# servidor responsavel por processamento de comandos e logica de processos em protocolo Binario usando TCP
# Autor: Allan

import socket
import selectors
import sys
import types
import struct
import logging
from pathlib import Path
import shutil

# config dos logs
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("bin_server.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BinServer')

# caminho virtual - prisao no boot do servidor
raiz_fisica = Path("/tmp/server_tcp").resolve()

# constantes do protocolo
MSG_REQ = 0x01
MSG_RES = 0x02

# constantes de comandos
CMD_ADDFILE = 0x01
CMD_DELETE = 0x02
CMD_GETFILESLIST = 0x03
CMD_GETFILE = 0x04

# constantes de status
STATUS_SUCCESS = 0x01
STATUS_ERROR = 0x02

# estados da maquina de leitura
LER_CABECALHO = 1
LER_NOME = 2
LER_FILESIZE = 3
LER_DADOS = 4

# construtores de resposta binaria
def montar_cabecalho_resposta_base(comando_id, status_code):
    # empacota 3 bytes absolutos (tipo, comando, status)
    return struct.pack('!BBB', MSG_RES, comando_id, status_code)

def montar_resposta_erro(comando_id):
    # construtor de atalho para falhas
    return montar_cabecalho_resposta_base(comando_id, STATUS_ERROR)

# motor de rede (esqueleto)
def accept_wrapper(sock, sel):
    # aceita e configura conexao nao-bloqueante
    conn, addr = sock.accept()
    conn.setblocking(False)
    
    # inicializa o controle de estado binario do cliente
    data = types.SimpleNamespace(
        addr=addr,                  # endereco
        inb=bytearray(),            # buffer de entrada
        outb=bytearray(),           # buffer de saida   
        estado_atual=LER_CABECALHO, # maquina de estados
        bytes_necessarios=3,        # bytes necessarios
        comando_atual=None,         # comando atual
        tamanho_nome=0,             # tamanho do nome do arquivo
        nome_arquivo=b"",           # nome 
        tamanho_arquivo=0,          # tamanho do arquivo
        bytes_recebidos_arquivo=0,  # bytes recebidos
        fd_arquivo_disco=None,      # ponteiro pra gravar em disco com addfile
        pronto_para_fechar=False    # flag de fechamento
    )
    
    sel.register(conn, selectors.EVENT_READ, data=data)
    logger.info(f"connection established with {addr}")

def expurgar_sessao(key, sel):
    # isola variaveis de sessao
    sock = key.fileobj
    data = key.data
    
    if data.fd_arquivo_disco:   # estanca vazamento de e/s de disco
        try:
            data.fd_arquivo_disco.close() # força fechamento de ponteiro
            
        except Exception:
            pass
        
        data.fd_arquivo_disco = None  # destroi referencia
    
    try: 
        sel.unregister(sock)          # remove monitoramento do kernel
    except Exception:
        pass
    
    try: 
        sock.close()    # destroi FD de rede
    except Exception:
        pass

    logger.info(f"session purged and resources freed for {data.addr}")

def service_connection(key, mask, sel):
    # gerencia i/o bruto
    sock = key.fileobj
    data = key.data

    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(4096)
        except ConnectionResetError:
            recv_data = None

        if recv_data:
            # estende buffer com novos bytes
            data.inb.extend(recv_data)
            try:
                processar_maquina_estados(key, sel)
                
                if data.outb or getattr(data, 'fd_arquivo_disco', None):
                    sel.modify(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)

            except Exception as e:
                # se pacote binario for corrompido finaliza sessao
                logger.error(f"protocol corrupted by client {data.addr}: {e}")
                expurgar_sessao(key, sel)
                return
        else:
            # termino seguro de sessao sem fechar socket
            logger.info(f"connection lost with client {data.addr}")
            expurgar_sessao(key, sel)
            
            return

    if mask & selectors.EVENT_WRITE:
        
        if not data.outb and getattr(data, 'fd_arquivo_disco', None):
            try:
                chunk = data.fd_arquivo_disco.read(4096)
                if chunk:
                    data.outb.extend(chunk)

                else:
                    data.fd_arquivo_disco.close()
                    data.fd_arquivo_disco = None
                    logger.info(f"upload completed for {data.addr}")
                    reset_estado_leitura(data)

            except Exception as e:
                logger.error(f"disk read failure for {data.addr}: {e}") # disco com defeito ou arquivo deletado externamente durante leitura
                expurgar_sessao(key, sel)
    
                return

        # despachante esvazia buffer
        if data.outb:
            try:
                sent = sock.send(data.outb)
                del data.outb[:sent]

            except BlockingIOError:     # cliente derrubou conexao na hora que server enviaria bytes
                expurgar_sessao(key, sel)
                return
        
        # desliga escrita se nao tem mais nada
        if not data.outb and getattr(data, 'fd_arquivo_disco', None) is None:

            if data.pronto_para_fechar:
                expurgar_sessao(key, sel)

            else:
                sel.modify(sock, selectors.EVENT_READ, data=data)


def processar_maquina_estados(key, sel):
    # roteador de transicao baseado no estado atual
    data = key.data
    sock = key.fileobj

    # enquanto tiver bytes para estado atual
    while len(data.inb) >= data.bytes_necessarios:
        

        if data.estado_atual == LER_CABECALHO: 
            cabecalho = data.inb[:3] # separa 3 primeiros bytes do cabecalho
            msg_type, cmd_id, name_size = struct.unpack('!BBB', cabecalho) # extrai bytes pra leitura
            del data.inb[:3]         # desliza buffer depois de ler
            
            data.comando_atual = cmd_id  
            data.tamanho_nome = name_size
            data.estado_atual = LER_NOME
            data.bytes_necessarios = name_size
            
        elif data.estado_atual == LER_NOME:
            nome_bytes = data.inb[:data.tamanho_nome]
            data.nome_arquivo = nome_bytes.decode('utf-8')
            del data.inb[:data.bytes_necessarios]


            if data.comando_atual in [CMD_DELETE, CMD_GETFILESLIST, CMD_GETFILE]:
                exec_cmd_bin(data, sock, sel)

                
            elif data.comando_atual == CMD_ADDFILE:
                data.estado_atual = LER_FILESIZE
                data.bytes_necessarios = 4

        elif data.estado_atual == LER_FILESIZE:
            size_bytes = data.inb[:4]
            data.tamanho_arquivo = struct.unpack('!I', size_bytes)[0]
            del data.inb[:4]

            # resolve caminho usando raiz_fisica global
            alvo = (raiz_fisica / data.nome_arquivo).resolve()

            # valida prisão (path traversal)
            if alvo.is_relative_to(raiz_fisica):
                try:
                    data.fd_arquivo_disco = open(alvo, 'wb')
                    data.estado_atual = LER_DADOS
                    data.bytes_necessarios = 1  # entra no modo de escoamento continuo

                except PermissionError:
                    logger.error(f"permission denied to write file: {alvo.name}")
                    expurgar_sessao(key, sel)   # corta conexao p/ evitar dessincronia do payload

            else:
                logger.warning(f"blocked attempt for ADDFILE: {data.nome_arquivo}") # caso tentativa de path transversal
                
                expurgar_sessao(key, sel)       # corta conexao p/ evitar ingestao de lixo no buff


        elif data.estado_atual == LER_DADOS:
            falta = data.tamanho_arquivo - data.bytes_recebidos_arquivo
            bytes_a_gravar = data.inb[:falta]

            data.fd_arquivo_disco.write(bytes_a_gravar)
            tamanho_chunk = len(bytes_a_gravar)

            data.bytes_recebidos_arquivo += tamanho_chunk
            del data.inb[:tamanho_chunk]


            if data.bytes_recebidos_arquivo == data.tamanho_arquivo:
                # fecha conexao com disco
                data.fd_arquivo_disco.close()
                data.fd_arquivo_disco = None

                data.outb.extend(montar_cabecalho_resposta_base(CMD_ADDFILE, STATUS_SUCCESS))
                reset_estado_leitura(data)

        else:
            break


    
def exec_cmd_bin(data, sock, sel):
    # roteia e executa comandos binarios
    
    if data.comando_atual == CMD_DELETE:
        # calcula alvo absoluto usando raiz fisica
        alvo = (raiz_fisica / data.nome_arquivo).resolve()
        

        # valida se alvo esta dentro da prisao
        if alvo.is_relative_to(raiz_fisica) and alvo.is_file():
            try:
                # remove link do inode no SO
                alvo.unlink()
                logger.info(f"file deleted: {alvo.name} by client {data.addr}")
                
                # monta cabecalho de sucesso (tipo 2, cmd 2, status 1)
                resposta = montar_cabecalho_resposta_base(CMD_DELETE, STATUS_SUCCESS)


            except PermissionError:
                logger.error(f"permission denied when deleting: {alvo.name}")
                # monta cabecalho de erro (tipo 2, cmd 2, status 2)
                resposta = montar_resposta_erro(CMD_DELETE)


        else:
            logger.warning(f"invalid deletion or path traversal blocked: {data.nome_arquivo}")
            resposta = montar_resposta_erro(CMD_DELETE)
            
        # enfileira bytes no buffer de saida
        data.outb.extend(resposta)
        reset_estado_leitura(data)

        
    elif data.comando_atual == CMD_GETFILESLIST:
        arquivos_encontrados = []
        try:
            # varredura do diretorio plano
            for item in raiz_fisica.iterdir():
                if item.is_file():
                    arquivos_encontrados.append(item.name)
            
            # monta cabecalho de sucesso (3 bytes)
            resposta = bytearray(montar_cabecalho_resposta_base(CMD_GETFILESLIST, STATUS_SUCCESS))
            
            # empacota quantidade total de arquivos em 2 bytes (Big Endian)
            qtd_bytes = struct.pack('!H', len(arquivos_encontrados))
            resposta.extend(qtd_bytes)
            
            # laco estrito de empacotamento dinamico para cada arquivo
            for nome in arquivos_encontrados:
                nome_bytes = nome.encode('utf-8')
                tamanho_nome = len(nome_bytes)
                

                # valida regra do protocolo (de 1 a 255 bytes)
                if tamanho_nome > 255:
                    logger.warning(f"file ignored in listing (name too long): {nome}")
                    continue
                
                # empacota 1 byte (B) para tamanho e anexa nome
                resposta.extend(struct.pack('!B', tamanho_nome))
                resposta.extend(nome_bytes)
            
            logger.info(f"listing sent ({len(arquivos_encontrados)} files) to {data.addr}")
            

        except PermissionError:
            logger.error("permission error when listing root directory.")
            resposta = bytearray(montar_resposta_erro(CMD_GETFILESLIST))

        # injeta payload binario na saida
        data.outb.extend(resposta)
        reset_estado_leitura(data)

        
    elif data.comando_atual == CMD_GETFILE:
        alvo = (raiz_fisica / data.nome_arquivo).resolve()

        
        if alvo.is_relative_to(raiz_fisica) and alvo.is_file():
            try:
                tamanho_arquivo = alvo.stat().st_size    # descobre tamanho usando pathlib
                
                data.fd_arquivo_disco = open(alvo, 'rb') # abre arquivo e guarda ponteiro de sessao
                

                # monta cabecalho base e anexa 4 bytes do tamanho
                resposta = bytearray(montar_cabecalho_resposta_base(CMD_GETFILE, STATUS_SUCCESS))
                resposta.extend(struct.pack('!I', tamanho_arquivo))
                
                
                data.outb.extend(resposta) # injeta cabecalho
                
                logger.info(f"starting transfer of {alvo.name} ({tamanho_arquivo} bytes) to {data.addr}")
                

            except PermissionError:
                logger.error(f"permission denied to read: {alvo.name}")
                data.outb.extend(montar_resposta_erro(CMD_GETFILE))
                reset_estado_leitura(data)
        else:
            logger.warning(f"file not found or invalid: {data.nome_arquivo}")
            data.outb.extend(montar_resposta_erro(CMD_GETFILE))
            reset_estado_leitura(data)



def reset_estado_leitura(data):
    # reseta maquina de estados para aguardar proxima requisicao do client
    data.estado_atual = LER_CABECALHO
    data.bytes_necessarios = 3
    data.comando_atual = None
    data.tamanho_nome = 0
    data.nome_arquivo = ""
    
    # limpa variaveis residuais do addfile
    data.tamanho_arquivo = 0
    data.bytes_recebidos_arquivo = 0
    if data.fd_arquivo_disco:
        data.fd_arquivo_disco.close()
        data.fd_arquivo_disco = None



def popular_ambiente_teste(raiz_fisica):
    # previne acumulo de lixo entre reinicios: apaga a raiz e recria do zero
    if raiz_fisica.exists():
        shutil.rmtree(raiz_fisica)
    raiz_fisica.mkdir(parents=True, exist_ok=True)

    # cria estrutura de diretorios virtuais
    pasta_redteam = raiz_fisica / "redteam_tools"
    pasta_redteam.mkdir()
    
    pasta_utfpr = raiz_fisica / "utfpr_projects"
    pasta_utfpr.mkdir()
    
    pasta_importante = raiz_fisica / "important_notes"
    pasta_importante.mkdir()

    # arquivos soltos na raiz da prisao
    (raiz_fisica / "saas_notes.txt").write_text("ideas for automation and infrastructure on digitalocean.")
    (raiz_fisica / "hashcat_commands.txt").write_text("hashcat -m 1000 -a 0 hash.txt wordlist.txt")

    # popula subdiretorios com arquivos
    (pasta_redteam / "nmap_stealth.sh").write_text("#!/bin/bash\nnmap -sS -p- -T4 --min-rate=1000 target.com")
    (pasta_redteam / "wordlist_custom.txt").write_text("admin\n123456\npassword\nroot\n")
    
    (pasta_utfpr / "db_readme.md").write_text("# documentation of database modeling and orm")
    (pasta_utfpr / "pentest2025_report.pdf").write_bytes(b"%PDF-1.4\n% purposely corrupted pdf file for byte testing")
    
    (pasta_importante / "skyrim_battlemage.md").write_text("focus on destruction, heavy armor and black books rewards.")
    (pasta_importante / "StarWars.md").write_text("may the force be with you")
    
    print(f"[!] test environment populated at: {raiz_fisica}")


## OPERAÇÃO PRINCIPAL DE FLUXO
if __name__ == "__main__":

    raiz_fisica.mkdir(parents=True, exist_ok=True)  # cria diretorio efemero
    popular_ambiente_teste(raiz_fisica)             # popula ambiente

    # inicializa seletor
    sel = selectors.DefaultSelector()

    # config socket
    host, port = '127.0.0.1', 65432
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind((host, port))
    lsock.listen()
    lsock.setblocking(False)

    # registra socket
    sel.register(lsock, selectors.EVENT_READ, data=None)

    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj, sel)
                else:
                    service_connection(key, mask, sel)
    except KeyboardInterrupt:
        print("\n[!] Shutting down server...")
    finally:
        sel.close()