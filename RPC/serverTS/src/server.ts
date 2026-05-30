// codigo responsavel pela inicializacao do servidor e tratamento de solicitacoes do cliente via gRPC
// autor: Allan 

import 'dotenv/config';
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import path from 'path';
import { connectToDatabase } from './database/connection';
import { readMovie, listByActor, createMovie, updateMovie, deleteMovie, listByCategory } from './controllers/movieController';

// compilacao do contrato
const PROTO_PATH = path.resolve(__dirname, '../src/proto/movies.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
});

// extrai namespace com base no proto
const protoDescriptor = grpc.loadPackageDefinition(packageDefinition) as any;
const moviesProto = protoDescriptor.movies;

// tratamento de erros
function handleError(error: any, callback: grpc.sendUnaryData<any>) {
    callback({
        code: grpc.status.INVALID_ARGUMENT,
        details: error.message
    }, null);
}

// interceptor de mensagens entre cliente e servidor
function comTelemetria(nomeRpc: string, handler: Function) {
    return async (call: any, callback: any) => {
        // log de entrada
        console.log(`\n[->] rpc received: ${nomeRpc}`);
        console.log(`     payload:`, Object.keys(call.request).length ? call.request : '{ empty }');

        const tempoInicio = Date.now();

        // callback que inspeciona saida antes de saida pra rede
        const callbackInterceptado = (erro: any, resposta: any) => {
            const duracao = Date.now() - tempoInicio;
            
            if (erro) {
                console.log(`[x]  rpc rejected: ${nomeRpc} (${duracao}ms) | reason: ${erro.details}`);
            } else {
                console.log(`[<-] rpc finished: ${nomeRpc} (${duracao}ms)`);
            }
            
            // devolve fluxo original
            callback(erro, resposta);
        };

        // executa rota passando como callback
        await handler(call, callbackInterceptado);
    };
}

// motor de inicializacao
async function bootstrap() {
    try {
        const db = await connectToDatabase();
        const server = new grpc.Server();

        
        // mapeamento de assinaturas com interceptor
        server.addService(moviesProto.MovieService.service, {
            
            CreateMovie: comTelemetria('CreateMovie', async (call: any, callback: any) => {
                try {
                    const result = await createMovie(db, call.request);
                    callback(null, result[0]); 
                } catch (e) { handleError(e, callback); }
            }),

            UpdateMovie: comTelemetria('UpdateMovie', async (call: any, callback: any) => {
                try {
                    const result = await updateMovie(db, call.request.id, call.request);
                    callback(null, result[0]);
                } catch (e) { handleError(e, callback); }
            }),

            DeleteMovie: comTelemetria('DeleteMovie', async (call: any, callback: any) => {
                try {
                    await deleteMovie(db, call.request.id);
                    callback(null, { success: true });
                } catch (e) { handleError(e, callback); }
            }),

            ReadMovie: comTelemetria('ReadMovie', async (call: any, callback: any) => {
                try {
                    const result = await readMovie(db, call.request.id);
                    if (result.length === 0) {
                        return callback({
                            code: grpc.status.NOT_FOUND,
                            details: 'movie not found'
                        }, null);
                    }
                    callback(null, result[0]);
                } catch (e) { handleError(e, callback); }
            }),

            ListMoviesByActor: comTelemetria('ListMoviesByActor', async (call: any, callback: any) => {
                try {
                    const result = await listByActor(db, call.request.actor_name);
                    callback(null, { movies: result });
                } catch (e) { handleError(e, callback); }
            }),

            ListMoviesByCategory: comTelemetria('ListMoviesByCategory', async (call: any, callback: any) => {
                try {
                    const result = await listByCategory(db, call.request.category);
                    callback(null, { movies: result });
                } catch (e) { handleError(e, callback); }
            })
        });

        // abertura de porta sobre http/2
        const port = process.env.PORT;
        server.bindAsync(
            `0.0.0.0:${port}`,
            grpc.ServerCredentials.createInsecure(),
            (error, port) => {
                if (error) throw error;
                console.log(`[+] grpc server operational on port ${port}`);
            }
        );

    } catch (error) {
        console.error('critical initialization error:', error);
        process.exit(1);
    }
}

bootstrap();