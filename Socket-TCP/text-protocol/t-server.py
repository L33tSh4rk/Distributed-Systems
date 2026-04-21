# servidor responsavel por processamento de comandos e logica de processos em protocolo de texto usando TCP
# Autor: Allan

import socket
import selectors
import types
import string
import hmac
from pathlib import Path
import shutil


# dicionario simulado de db local
db_usuarios = {
    "admin": "c7ad44cbad762a5da0a452f9e854fdc1e0e7a52a38015f23f3eab1d80b931dd472634dfac71cd34ebc35d16ab7fb8a90c81f975113d6c7538dc69dd8de9077ec",
    "aluno": "f74f4d08330936fd26306b27d2e56f2ee002d1862d534c563325ee53b8bd0e3a2ca660849782fd44271364dabbf6888380be4d1b7c69a568bd5ecf4b66e2dc09",
    "hacker": "985aa195c09fb7d64a4bb24cfe51fb1f13ebc444c494e765ee99d6c3ef46557c757787f8f5a6e0260d2e0e846d263fbfbe1311c884bb0bf9792f8778a4434327"
}

# caminho virtual - prisao no boot do servidor
raiz_fisica = Path("/tmp/server_tcp").resolve()

# ESTADOS E E/S
def accept_wrapper(sock):
    # aceita conexao do cliente
    conn, addr = sock.accept()
    
    # configura nao-bloqueante
    conn.setblocking(False)
    
    # inicializa estado da sessao
    data = types.SimpleNamespace(
        addr=addr,                  # endereco
        inb=b"",                    # in_buffer
        outb=b"",                   # out_buffer
        autenticado=False,          # flag de autenticacao
        usuario=None,               # nome do usuario
        raiz_pessoal=None,          # raiz pessoal
        diretorio_atual=None,       # dir atual
        pronto_para_fechar=False    # flag para fechar sessao
    )
    
    # registra apenas leitura inicial
    sel.register(conn, selectors.EVENT_READ, data=data)

def service_connection(key, mask):
    # gerencia i/o da conexao
    sock = key.fileobj
    data = key.data

    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)  # le bytes da rede
            
        except ConnectionResetError:
            recv_data = None

        if recv_data:
            data.inb += recv_data         # anexa bytes ao buffer
            
            processar_buffer_entrada(key) # extrai mensagens completas
            
        else:
            # encerra conexao
            sel.unregister(sock)
            sock.close()

    if mask & selectors.EVENT_WRITE:
        if data.outb:
            sent = sock.send(data.outb)     # envia dados do buffer
            data.outb = data.outb[sent:]    # desliza buffer
        
        if not data.outb:
            if data.pronto_para_fechar:
                sel.unregister(sock)    # remove cliente do monitoramento do SO
                
                sock.close()            # destroi FD e libera porta
            else:
                sel.modify(sock, selectors.EVENT_READ, data=data)   # remove evento de escrita

def processar_buffer_entrada(key):
    # roteia comandos recebidos
    data = key.data
    sock = key.fileobj

    while b'\n' in data.inb:
        # recorta primeira mensagem
        linha_bytes, _, resto = data.inb.partition(b'\n')
        data.inb = resto
        
        # decodifica utf-8
        mensagem = linha_bytes.decode('utf-8').strip()
        
        if not mensagem:
            continue
            
        # processa comando
        if mensagem.startswith("CONNECT"):
            if data.autenticado:
                data.outb += b"ERROR - user already authenticated\n"
            else:
                data.autenticado, data.usuario = valida_hash(mensagem)
            
                if not data.autenticado:
                    data.outb += b"ERROR : unable to authenticate user. usage: 'CONNECT user, password'\n"
                else:
                    data.outb += b"SUCCESS\n"

                    # cria diretorios separados pra cada usuario
                    pasta_pessoal = raiz_fisica / data.usuario
                    pasta_pessoal.mkdir(exist_ok=True)
                    
                    # tranca usuario na sua prisão
                    data.raiz_pessoal = pasta_pessoal
                    data.diretorio_atual = str(data.raiz_pessoal)   

        elif not data.autenticado:
            data.outb += b"ERROR : authentication required\n"

        else: 
            if mensagem == "WHOAMI":
                # empacota nome do usuario e envia
                data.outb += (data.usuario + "\n").encode('utf-8')

            elif mensagem == "HELP":
                # string de linha unica (sem quebrar framing do client)
                ajuda = (
                    "COMMANDS -> "
                    "WHOAMI | "
                    "PWD | "
                    "CHDIR <target> | "
                    "GETFILES | "
                    "GETDIRS | "
                    "EXIT"
                )
                data.outb += (ajuda + "\n").encode('utf-8')

            elif mensagem == "PWD":
                # gera caminho em texto plano
                caminho_ilusorio_str = pwd(data)
                
                resposta = caminho_ilusorio_str + "\n" # acopla delimitador
                data.outb += resposta.encode('utf-8') # converte para array de bytes


            elif mensagem.startswith("CHDIR "):
                alvo = mensagem[6:].strip()
                status_str = chdir(data, alvo)
                
                data.outb += (status_str + "\n").encode('utf-8') # formatacao e codificacao


            elif mensagem == "GETFILES":
                bloco_bytes = getfiles(data) # recebe bloco binario formatado com quebras de linha
                
                data.outb += bloco_bytes # enfileira no buffer do sistema


            elif mensagem == "GETDIRS":
                
                bloco_bytes = getdirs(data) # recebe o bloco binario formatado
                
                data.outb += bloco_bytes # enfileira no buffer de saida do sistema


            elif mensagem == "EXIT":
                data.pronto_para_fechar = True
                data.outb += b"SUCCESS_EXIT\n"


            else:
                data.outb += b"command not found. use HELP.\n"
        
        # evento de escrita
        sel.modify(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)


# FUNÇÕES DE SISTEMA
def valida_hash(mensagem):
    # separa comando de "usuario, hash"
    payload = mensagem[8:]
    
    # divide primeira virgula
    partes = payload.split(",", 1)
    
    # barra tentativa sem virgula
    if len(partes) != 2:
        return False, None
        
    # remove espacos
    usuario = partes[0].strip()
    hash_recebido = partes[1].strip()
    
    # verifica 128 caracteres e hexadecimal puro
    if len(hash_recebido) != 128 or not all(c in string.hexdigits for c in hash_recebido):
        return False, None
        
    # busca hash no banco
    hash_esperado = db_usuarios.get(usuario)
    
    # falha silenciosa se usuario nao existir
    if not hash_esperado:
        return False, None
        
    # compara hashes
    if hmac.compare_digest(hash_recebido.lower(), hash_esperado.lower()):
        return True, usuario
        
    return False, None



def popular_ambiente_teste(raiz_fisica):
    if raiz_fisica.exists():
        shutil.rmtree(raiz_fisica)
    raiz_fisica.mkdir(parents=True, exist_ok=True)

    # criação dos homes de cada usuario
    for usuario in db_usuarios.keys():

        home_usuario = raiz_fisica / usuario
        home_usuario.mkdir(parents=True, exist_ok=True)

        # povoamento específico por perfil
        if usuario == "admin":
            pasta_auditoria = home_usuario / "audit"
            pasta_auditoria.mkdir()
            pasta_configuracoes = home_usuario / "configs"
            pasta_configuracoes.mkdir()

            (pasta_configuracoes / "server_config.conf").write_text("# global server configurations")
            (pasta_auditoria / "user_audit.log").write_text("2026-04-21: root access detected.")
            (home_usuario / "backup_script.sh").write_text("#!/bin/bash\ntar -czf backup.tar.gz /home")
        
        elif usuario == "aluno":
            pasta_aluno = home_usuario / "utfpr"
            pasta_aluno.mkdir()
            pasta_importante = home_usuario / "important"
            pasta_importante.mkdir()

            (pasta_aluno / "algorithms_notes.txt").write_text("study binary trees and graphs.")
            (pasta_aluno / "db_final_project.sql").write_text("CREATE TABLE users (id INT, name TEXT);")
            (pasta_aluno / "class_schedule.pdf").write_bytes(b"%PDF-1.4 simulated")
            (pasta_importante / "skyrim_battlemage.md").write_text("focus on destruction, heavy armor and black books rewards.")
            (pasta_importante / "StarWars.md").write_text("may the force be with you")

        elif usuario == "hacker":
            pasta_hacker = home_usuario / "methodologies"
            pasta_hacker.mkdir()
            ferramentas_hacker = home_usuario / "tools"
            ferramentas_hacker.mkdir()

            (pasta_hacker / "redteam_recon.md").write_text("# targets identified on the internal network")
            (pasta_hacker / "osint_research.txt").write_text("search for metadata in public files.")
            (ferramentas_hacker / "payload_generator.py").write_text("# generates shellcode payloads")

    print(f"[!] multi-user environment populated at: {raiz_fisica}")


# COMANDOS
def pwd(data):
    # path fisico -> descobre onde o cliente realmente esta
    caminho_real = Path(data.diretorio_atual)
    
    # path virtual -> calcula distancia entre raiz da prisao e onde esta
    if caminho_real == data.raiz_pessoal:
        caminho_ilusorio = "/"
    else:
        # revela aminho interno
        caminho_ilusorio = "/" + str(caminho_real.relative_to(data.raiz_pessoal))
        
    return caminho_ilusorio



def chdir(data, alvo_cliente):    
    # força raiz do servidor como raiz real
    if alvo_cliente.startswith("/"):
        alvo_cliente = alvo_cliente.lstrip("/")
        base_calculo = data.raiz_pessoal
    else:
        base_calculo = Path(data.diretorio_atual)
        
    # resolve os '..' pra descobrir destino real
    caminho_tentativa = (base_calculo / alvo_cliente).resolve()
    
    # verifica se cliente esta dentro do path do server
    if caminho_tentativa.is_relative_to(data.raiz_pessoal) and caminho_tentativa.is_dir():
        data.diretorio_atual = str(caminho_tentativa) # atualiza no servidor
        
        return "SUCCESS"

    else:
        return "ERROR - directory not found" # se cliente tenta escapar ou pasta nao existir (para possivel tentativa de ataque de path transversal)


def getfiles(data):
    # aponta para a fonte da verdade fisica no servidor
    caminho_real = Path(data.diretorio_atual)
    
    arquivos_encontrados = []
    
    # varre itens dentro do diretorio atual
    try:
        for item in caminho_real.iterdir():

            if item.is_file(): # filtro
                arquivos_encontrados.append(item.name)

    except PermissionError:
        return b"ERROR - permission denied\n"
        
    quantidade = len(arquivos_encontrados)
    
    linhas_resposta = [str(quantidade)]         # constroi linha de cabeçalho (string utf)

    
    linhas_resposta.extend(arquivos_encontrados) # anexa nome de arquivos na lista

    
    bloco_texto = "\n".join(linhas_resposta)
    
    bloco_texto_final = bloco_texto + "\n"      # acopla ultimo \n para fechamento de framing do cliente e converte
    
    return bloco_texto_final.encode('utf-8')



def getdirs(data):
    
    caminho_real = Path(data.diretorio_atual) # aponta para diretorio atual fisico do server
    diretorios_encontrados = []

    try:
        for item in caminho_real.iterdir(): # itera sobre itens do diretorio
            
            if item.is_dir():
                diretorios_encontrados.append(item.name)
    except PermissionError:
        return b"ERROR - permission denied\n"
    
    quantidade = len(diretorios_encontrados)    # conta quantidade de diretorios
    
    linhas_resposta = [str(quantidade)]         # inicia lista com quantidade em string
    
    linhas_resposta.extend(diretorios_encontrados) # anexa nomes de dirs encontrados
    
    bloco_texto = "\n".join(linhas_resposta)    # junta tudo
    
    bloco_texto_final = bloco_texto + "\n"      # fecha framing do cliente
    
    return bloco_texto_final.encode('utf-8')    # converte para utf



## OPERAÇÃO PRINCIPAL DE FLUXO
if __name__ == "__main__":
 
    raiz_fisica.mkdir(parents=True, exist_ok=True)  # cria diretorio efemero
    popular_ambiente_teste(raiz_fisica)             # popula ambiente

    # inicializa seletor
    sel = selectors.DefaultSelector()

    # config principal do socket
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
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
    except KeyboardInterrupt:
        print("\n[!] Shutting down server...")
    finally:
        sel.close()