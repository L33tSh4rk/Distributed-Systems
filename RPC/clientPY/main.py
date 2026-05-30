# codigo responsavel por fazer as requisições ao servidor via gRPC
# autor: Allan

import os
import grpc
from proto import movies_pb2_grpc
from proto import movies_pb2

# formata e imprime filmes respeitando limites de terminal
def exibir_filmes(filmes, listagem_lote=False):
    if not filmes:
        print("[-] no records found.")
        return

    print(f"[+] success. records returned: {len(filmes)}\n")
    
    for i, filme in enumerate(filmes, 1):
        print(f"[*] record {i}")
        print(f"    id      : {filme.id}")
        print(f"    title  : {filme.title} ({filme.year})")
        print(f"    type    : {filme.type}")
        
        if filme.genres:
            print(f"    genres : {', '.join(filme.genres)}")
        if filme.cast:
            print(f"    cast  : {', '.join(filme.cast)}")
        if filme.directors:
            print(f"    directors : {', '.join(filme.directors)}")
            
        if filme.plot:
            sinopse_limpa = filme.plot.replace('\n', ' ')
            
            # avalia escopo para truncar textos longos em listagens
            if not listagem_lote:
                print(f"    plot : {sinopse_limpa.lower()}")
            else:
                teto_visual = 120
                sinopse = sinopse_limpa if len(sinopse_limpa) <= teto_visual else sinopse_limpa[:(teto_visual-3)] + '...'
                print(f"    plot : {sinopse.lower()}")
        print("-" * 40)

# ponto de entrada do cliente interativo
def run():

    # busca url resolvida pelo docker ou cai para localhost se executado nativamente
    servidor_url = os.environ.get('GRPC_SERVER_URL', 'localhost:3000')
    
    
    # inicializa tunel http/2 sem tls
    canal = grpc.insecure_channel(servidor_url)
    
    # instancia representante local do servidor ts
    stub = movies_pb2_grpc.MovieServiceStub(canal)

    

    print("="*50)
    print(" RPC-CLI | CONNECTED")
    print(" COMMANDS: READ, LSACT, LSCATG, CREATE, UPDATE, DELETE, EXIT")
    print("="*50)

    while True:
        try:
            # separa por qualquer espaco para identificar argumentos ilegais
            entrada = input("\nrpc-cli> ").strip().split()
            
            if not entrada:
                continue
                
            comando = entrada[0].upper()
            
            # rejeita argumentos passados na mesma linha
            if len(entrada) > 1:
                print(f"[-] syntax error: command '{comando}' does not accept inline arguments.")
                print("    type only the command. data will be requested next.")
                continue

            
            # roteador de comandos pro cliente
            if comando == 'EXIT':
                print("[*] closing grpc channel.")
                canal.close()
                break

            elif comando == 'READ':
                alvo = input("target id: ").strip()
                requisicao = movies_pb2.MovieIdRequest(id=alvo)
                resposta = stub.ReadMovie(requisicao)
                exibir_filmes([resposta], listagem_lote=False)

            elif comando == 'LSACT':
                ator = input("actor name: ").strip()
                requisicao = movies_pb2.ActorRequest(actor_name=ator)
                resposta = stub.ListMoviesByActor(requisicao)
                exibir_filmes(resposta.movies, listagem_lote=True)

            elif comando == 'LSCATG':
                categoria = input("category (e.g.: action): ").strip()
                requisicao = movies_pb2.CategoryRequest(category=categoria)
                resposta = stub.ListMoviesByCategory(requisicao)
                exibir_filmes(resposta.movies, listagem_lote=True)

            elif comando == 'DELETE':
                alvo = input("target id for deletion: ").strip()
                requisicao = movies_pb2.MovieIdRequest(id=alvo)
                resposta = stub.DeleteMovie(requisicao)
                if resposta.success:
                    print("[+] record permanently deleted from database.")

            elif comando == 'CREATE':
                titulo = input("title: ").strip()
                ano = int(input("year: ").strip())
                tipo = input("type (movie/series): ").strip()
                
                print("\naccepted genres: \naction, adventure, animation, biography, comedy, crime, documentary, drama, family, fantasy, \nhistory, horror, music, musical, mystery, romance, sci-fi, sport, thriller, war, western\n")
                generos = [g.strip() for g in input("genres (comma separated): ").split(',') if g.strip()]
                elenco = [e.strip() for e in input("cast (comma separated): ").split(',') if e.strip()]
                diretores = [d.strip() for d in input("directors (comma separated): ").split(',') if d.strip()]
                sinopse = input("plot: ").strip()
                
                requisicao = movies_pb2.CreateMovieRequest(
                    title=titulo,
                    year=ano,
                    type=tipo,
                    genres=generos,
                    cast=elenco,
                    directors=diretores,
                    plot=sinopse
                )
                resposta = stub.CreateMovie(requisicao)
                exibir_filmes([resposta], listagem_lote=False)

            elif comando == 'UPDATE':
                alvo = input("target id: ").strip()


                try:
                    busca_req = movies_pb2.MovieIdRequest(id=alvo)
                    filme_atual = stub.ReadMovie(busca_req)
                    print("\n[*] current state of target record:")
                    exibir_filmes([filme_atual], listagem_lote=False)
                except grpc.RpcError as e:
                    # aborta se ponteiro for invalido/nao existir
                    print(f"[-] pre-inspection failed: {e.details()}")
                    continue


                print("modifiable fields: TITLE, YEAR, TYPE, PLOT, CAST, DIRECTORS, GENRES")
                campo = input("field to modify: ").strip().upper()
                
                # constroi dicionario de argumentos para campos optional do proto
                kwargs = {'id': alvo}
                
                if campo == 'TITLE': kwargs['title'] = input("new title: ").strip()
                elif campo == 'YEAR': kwargs['year'] = int(input("new year: ").strip())
                elif campo == 'TYPE': kwargs['type'] = input("new type: ").strip()
                elif campo == 'PLOT': kwargs['plot'] = input("new plot: ").strip()
                elif campo in ['CAST', 'DIRECTORS', 'GENRES']:
                    lista = [item.strip() for item in input(f"new {campo.lower()} (comma separated): ").split(',') if item.strip()]
                    if campo == 'CAST': kwargs['cast'] = lista
                    elif campo == 'DIRECTORS': kwargs['directors'] = lista
                    elif campo == 'GENRES': kwargs['genres'] = lista
                else:
                    print("[-] invalid field. use one of the following: TITLE, YEAR, TYPE, PLOT, CAST, DIRECTORS, GENRES")
                    continue
                
                requisicao = movies_pb2.UpdateMovieRequest(**kwargs)
                resposta = stub.UpdateMovie(requisicao)
                exibir_filmes([resposta], listagem_lote=False)

            else:
                print("[-] unrecognized command.")
                print("[-] VALID COMMANDS: READ, LSACT, LSCATG, CREATE, UPDATE, DELETE, EXIT")

        # intercepta excecoes lancadas pelo ts
        except grpc.RpcError as e:
            print(f"[-] server error: {e.details()}")
        except ValueError:
            print("[-] error: invalid type input (e.g.: letter where number expected).")
        except KeyboardInterrupt:
            print("\n[*] manual interrupt. closing grpc channel.")
            canal.close()
            break

if __name__ == '__main__':
    run()