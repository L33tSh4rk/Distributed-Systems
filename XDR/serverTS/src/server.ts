// codigo responsavel pela inicializacao do servidor e tratamento de solicitacoes
// autor: Allan

import 'dotenv/config';
import * as net from 'net';
import { RequestPayload, ResponsePayload } from './proto/loader';
import { connectToDatabase } from './database/connection';
import { readMovie, listByActor, createMovie, updateMovie, deleteMovie, listByCategory } from './controllers/movieController';

// inicializa servidor XDR
async function bootstrap() {
    try {
        const db = await connectToDatabase();
        
        const server = net.createServer((socket: net.Socket) => {
            console.log('new client connected');

            socket.on('data', async (data: Buffer | string) => {
                try {
                    // bloqueia execucao se tcp tentar entregar texto puro
                    if (typeof data === 'string') {
                        throw new Error('server only accepts binary buffers');
                    }

                    // converte buffer de node para tipo obrigatorio do protobuf
                    const binaryData = new Uint8Array(data);

                    // decodifica buffer em objeto typed
                    const request = RequestPayload.decode(binaryData) as any;


                    if (!request.operation) {
                        throw new Error('operation not provided');
                    }

                    console.log(`operation received: ${request.operation}`);

                    // vetor de resposta padrao
                    let responseData: Array<any> = [];

                    // roteador centralizado
                    switch (request.operation) {
                        case 'create':
                            responseData = await createMovie(db, request.movieData);
                            break;
                            
                        case 'read':
                            responseData = await readMovie(db, request.movieId);
                            break;
                            
                        case 'update':
                            responseData = await updateMovie(db, request.movieId, request.movieData);
                            break;
                            
                        case 'delete':
                            await deleteMovie(db, request.movieId);
                            break;
                            
                        case 'list_actor':
                            responseData = await listByActor(db, request.filterActor);
                            break;
                            
                        case 'list_category':
                            responseData = await listByCategory(db, request.filterCategory);
                            break;
                            
                        default:
                            // interrupcao
                            throw new Error('unknown operation');
                    }
                    
                    // empacota resposta resolvida pelo switch e devolve
                    const responseMsg = ResponsePayload.create({ 
                        success: true, 
                        data: responseData 
                    });
                    socket.end(ResponsePayload.encode(responseMsg).finish());

                } catch (error: any) {
                    // rota de fuga
                    console.log(`processing error: ${error.message.toLowerCase()}`);
                    
                    // empacota erro respeitando camelcase
                    const errorMsg = ResponsePayload.create({ 
                        success: false, 
                        errorMessage: error.message 
                    });
                    
                    socket.end(ResponsePayload.encode(errorMsg).finish());
                }
            });

            socket.on('error', () => {
                console.log('error: connection lost by the client');
            });
        });

        const port = Number(process.env.PORT) || 3000;
        server.listen(port, () => {
            console.log(`tcp server listening on port ${port}`);
        });

    } catch (error) {
        console.log('fatal error: server aborted due to database failure');
        process.exit(1);
    }
}

bootstrap();