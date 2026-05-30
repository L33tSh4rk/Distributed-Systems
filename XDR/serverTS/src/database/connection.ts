// codigo responsavel pela conexao com banco de dados
// autor: Allan


import { MongoClient, Db } from 'mongodb';

export async function connectToDatabase(): Promise<Db> {
    // extrai uri
    const uri = process.env.MONGO_URI;
    
    // barreira fail-fast para infraestrutura mal configurada
    if (!uri) {
        throw new Error('MONGO_URI environment variable not defined');
    }

    const client = new MongoClient(uri);
    await client.connect();
    
    console.log('connection to mongodb established');
    return client.db('sample_mflix');
}