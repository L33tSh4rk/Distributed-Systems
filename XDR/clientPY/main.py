# codigo responsavel por fazer as requisições ao servidor TCP.
# autor: Allan


import socket
import os
from proto import movies_pb2

# empacota logica de rede para ser acionada sob demanda
def disparar_requisicao(requisicao):
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # captura do ambiente com fallback para localhost em uso isolado
    host = os.getenv('SERVER_HOST', '127.0.0.1')
    porta = int(os.getenv('SERVER_PORT', 3000))
    

    try:
        cliente.connect(('127.0.0.1', 3000))
        buffer_saida = requisicao.SerializeToString()
        cliente.sendall(buffer_saida)

        # loop de absorcao de fragmentos tcp
        chunks = []
        while True:
            pedaco = cliente.recv(4096)
            if not pedaco:
                break
            chunks.append(pedaco)
            
        buffer_entrada = b''.join(chunks) # forma o buffer de entrada
        
        resposta = movies_pb2.ResponsePayload()
        resposta.ParseFromString(buffer_entrada) # desserializa
        
        return resposta

    except Exception as e:
        return f"erro critico de rede: {str(e).lower()}"
    finally:
        cliente.close()

# formatador de saida
def exibir_resposta(resposta):
    if type(resposta) == str:
        print(resposta)
        return

    if not resposta.success:
        print(f"[-] operation failed: {resposta.error_message.lower()}")
    else:
        qtd = len(resposta.data)
        print(f"[+] success. returned records: {qtd}\n")
        
        if qtd > 0:
            for index, item in enumerate(resposta.data, 1):
                print(f"[*] record {index}")
                
                # extrai o ponteiro de memoria
                if item._id:
                    print(f"    id      : {item._id}")
                    
                print(f"    title  : {item.title.lower()} ({item.year})")
                
                if item.type:
                    print(f"    type    : {item.type.lower()}")
                    
                # arrays no protobuf soldados com join
                if len(item.genres) > 0:
                    print(f"    genres : {', '.join(item.genres).lower()}")
                    
                if len(item.cast) > 0:
                    print(f"    cast  : {', '.join(item.cast).lower()}")
                    
                if len(item.directors) > 0:
                    print(f"    directors : {', '.join(item.directors).lower()}")
                    
                if item.plot:
                    # limita sinopse para nao estourar buffer visual
                    sinopse_limpa = item.plot.replace('\n', ' ')
                    sinopse = sinopse_limpa if len(sinopse_limpa) < 300 else sinopse_limpa[:297] + '...'
                    print(f"    plot : {sinopse.lower()}")
                    
                print("") 


# motor de terminal interativo
def iniciar_terminal():
    print("="*50)
    print("XDR TCP CLIENT - Mflix")
    print("comandos: LSACT, LSCATG, READ, CREATE, UPDATE, DELETE, EXIT")
    print("="*50)

    while True:
        try:
            # captura entrada limpando espacos e padronizando para maiusculas
            comando = input("\nxdr-cli> ").strip().upper()

            if comando == 'EXIT':
                print("closing terminal...")
                break
                
            if comando == '':
                continue

            requisicao = movies_pb2.RequestPayload()

            # roteamento de comandos
            if comando == 'READ':
                requisicao.operation = 'read'
                requisicao.movie_id = input("target id: ").strip()
                
            elif comando == 'DELETE':
                requisicao.operation = 'delete'
                requisicao.movie_id = input("target id for annihilation: ").strip()
                
            elif comando == 'LSACT':
                requisicao.operation = 'list_actor'
                requisicao.filter_actor = input("actor name (first letters capitalized): ").strip()
                
            elif comando == 'LSCATG':
                requisicao.operation = 'list_category'
                requisicao.filter_category = input("target category: ").strip()
                
            elif comando == 'CREATE':
                requisicao.operation = 'create'
                requisicao.movie_data.title = input("movie title: ").strip()
                requisicao.movie_data.year = int(input("release year: ").strip())
                requisicao.movie_data.type = input("type (movie/series): ").strip()
                
                # captura e limpa arrays
                generos = input("genres (comma separated): ").split(',')
                requisicao.movie_data.genres.extend([g.strip() for g in generos if g.strip()])
                
                elenco = input("cast (comma separated): ").split(',')
                requisicao.movie_data.cast.extend([e.strip() for e in elenco if e.strip()])
                
                direcao = input("directors (comma separated): ").split(',')
                requisicao.movie_data.directors.extend([d.strip() for d in direcao if d.strip()])
                
                requisicao.movie_data.plot = input("plot: ").strip()


            elif comando == 'UPDATE':
                requisicao.operation = 'update'
                requisicao.movie_id = input("id alvo para mutacao: ").strip()
                
                print("available fields: TITLE, YEAR, TYPE, GENRES, CAST, DIRECTORS, PLOT")
                campo = input("digite o campo que deseja alterar: ").strip().upper()
                
                if campo == 'TITLE':
                    requisicao.movie_data.title = input("new title: ").strip()
                elif campo == 'YEAR':
                    requisicao.movie_data.year = int(input("new year: ").strip())
                elif campo == 'TYPE':
                    requisicao.movie_data.type = input("new type (e.g. movie, series): ").strip()
                elif campo == 'PLOT':
                    requisicao.movie_data.plot = input("new plot: ").strip()

                elif campo in ['CAST', 'DIRECTORS', 'GENRES']:
                    lista = input(f"new {campo.lower()} (comma separated): ").split(',')
                    limpos = [item.strip() for item in lista if item.strip()]
                    
                    # roteamento dinamico para o campo de array correto
                    if campo == 'CAST': requisicao.movie_data.cast.extend(limpos)
                    elif campo == 'DIRECTORS': requisicao.movie_data.directors.extend(limpos)
                    elif campo == 'GENRES': requisicao.movie_data.genres.extend(limpos)
                else:
                    print("[-] invalid field for mutation. aborting operation.")
                    continue

            else:
                print("[-] invalid command. use: LSACT, LSCATGG, READ, CREATE, UPDATE, DELETE, EXIT")
                continue

            # executa disparo e exibe formato
            resposta = disparar_requisicao(requisicao)
            exibir_resposta(resposta)

        except ValueError:
            print("[-] type error. you entered text where a number was expected.")
        except KeyboardInterrupt:
            print("\nclosing terminal...")
            break

if __name__ == '__main__':
    iniciar_terminal()