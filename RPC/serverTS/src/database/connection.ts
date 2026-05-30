// codigo responsavel pela conexao com banco de dados
// autor: Allan

import { MongoClient, Db } from 'mongodb';

export async function connectToDatabase(): Promise<Db> {
    // extrai uri
    const uri = process.env.MONGO_URI;
    
    // barreira fail-fast para infraestrutura mal configurada
    if (!uri) {
        throw new Error('environment variable MONGO_URI not defined');
    }

    const client = new MongoClient(uri);
    await client.connect();
    
    console.log('connection with mongodb established');
    return client.db('sample_mflix');
}