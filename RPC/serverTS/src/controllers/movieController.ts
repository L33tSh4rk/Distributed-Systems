// codigo responsavel pelo CRUD e filtros do servidor utilizando gRPC
// Autor: Allan


import { Db, ObjectId } from 'mongodb';

// listas de validacao de metadados
const validTypes = new Set(['movie', 'series']);

const validGenres = new Set([
    'action', 'adventure', 'animation', 'biography', 'comedy', 
    'crime', 'documentary', 'drama', 'family', 'fantasy', 
    'history', 'horror', 'music', 'musical', 'mystery', 
    'romance', 'sci-fi', 'sport', 'thriller', 'war', 'western'
]);

// valida integridade de metadados antes de tocar no banco
function validateMetadata(type?: string, genres?: string[]) {
    if (type && !validTypes.has(type.toLowerCase().trim())) {
        throw new Error(`invalid type '${type}'. use: movie or series.`);
    }

    if (genres && genres.length > 0) {
        for (const genre of genres) {
            if (!validGenres.has(genre.toLowerCase().trim())) {
                const lista = Array.from(validGenres).sort().join(', ');
                throw new Error(`invalid genre '${genre}'.\naccepted genres: ${lista}`);
            }
        }
    }
}

// converte bson para objeto compativel com contrato protobuf
function sanitizeMovie(movie: any) {
    if (!movie) return null;
    
    const { _id, ...rest } = movie;
    return {
        id: _id.toString(), // mapeia chave interna para chave publica do proto
        ...rest,
        released: movie.released instanceof Date ? movie.released.toISOString() : (movie.released || ''),
        lastupdated: movie.lastupdated instanceof Date ? movie.lastupdated.toISOString() : (movie.lastupdated || '')
    };
}

// busca filme por id
export async function readMovie(db: Db, movieId: string) {
    if (!movieId) throw new Error('movie id not provided');
    if (!ObjectId.isValid(movieId)) throw new Error('invalid id format');
    
    const objectId = new ObjectId(movieId);
    const movie = await db.collection('movies').findOne({ _id: objectId });
    
    if (!movie) throw new Error('movie not found');
    
    return [sanitizeMovie(movie)]; 
}

// lista filmes por ator
export async function listByActor(db: Db, actorName: string) {
    if (!actorName) throw new Error('actor name not provided');
    
    // aplica busca regex ignorando case
    const movies = await db.collection('movies')
        .find({ cast: { $regex: actorName, $options: 'i' } })
        .limit(50)
        .toArray();
        
    return movies.map(sanitizeMovie);
}

// insere novo registro de filme
export async function createMovie(db: Db, movieData: any) {
    if (!movieData) throw new Error('movie data not provided');
    
    if (!movieData.title || movieData.title.trim() === '') {
        throw new Error('movie title cannot be empty');
    }

    if (!movieData.year || movieData.year < 1888) {
        throw new Error('invalid release year');
    }

    validateMetadata(movieData.type, movieData.genres);

    const { _id, ...dataToInsert } = movieData;
    
    const result = await db.collection('movies').insertOne(dataToInsert);
    if (!result.acknowledged) throw new Error('insert operation failed');
    
    const insertedMovie = await db.collection('movies').findOne({ _id: result.insertedId });
    return [sanitizeMovie(insertedMovie)];
}

// atualiza campos explicitamente enviados via grpc
export async function updateMovie(db: Db, movieId: string, updateData: any) {
    if (!movieId) throw new Error('movie id not provided');
    if (!ObjectId.isValid(movieId)) throw new Error('invalid id format');
    if (!updateData) throw new Error('update data not provided');
    
    validateMetadata(updateData.type, updateData.genres);

    const objectId = new ObjectId(movieId);
    const dataToUpdate: any = {};
    
    // avalia estado undefined gerado pelo modificador optional do proto3
    if (updateData.title !== undefined) dataToUpdate.title = updateData.title.trim();
    if (updateData.type !== undefined) dataToUpdate.type = updateData.type.trim();
    if (updateData.plot !== undefined) dataToUpdate.plot = updateData.plot.trim();
    
    if (updateData.year !== undefined) {
        if (updateData.year < 1888) throw new Error('invalid release year');
        dataToUpdate.year = updateData.year;
    }
    
    // processa arrays que grpc inicializa vazios por padrao
    if (updateData.genres && updateData.genres.length > 0) dataToUpdate.genres = updateData.genres;
    if (updateData.cast && updateData.cast.length > 0) dataToUpdate.cast = updateData.cast;
    if (updateData.directors && updateData.directors.length > 0) dataToUpdate.directors = updateData.directors;
    
    if (Object.keys(dataToUpdate).length === 0) {
        throw new Error('no valid data provided for update');
    }
    
    const result = await db.collection('movies').updateOne(
        { _id: objectId },
        { $set: dataToUpdate }
    );
    
    if (result.matchedCount === 0) throw new Error('movie not found for update');
    
    const updatedMovie = await db.collection('movies').findOne({ _id: objectId });
    return [sanitizeMovie(updatedMovie)];
}

// remove registro fisico do banco
export async function deleteMovie(db: Db, movieId: string) {
    if (!movieId) throw new Error('movie id not provided');
    if (!ObjectId.isValid(movieId)) throw new Error('invalid id format');
    
    const objectId = new ObjectId(movieId);
    const result = await db.collection('movies').deleteOne({ _id: objectId });
    
    if (result.deletedCount === 0) throw new Error('movie not found for deletion');
    
    // retorna
    return true;
}

// lista filmes filtrando por categoria
export async function listByCategory(db: Db, category: string) {
    if (!category) throw new Error('category not provided');
    
    const normalizedCategory = category.toLowerCase().trim();

    if (!validGenres.has(normalizedCategory)) {
        const categoriasLista = Array.from(validGenres).sort().join(', ');
        throw new Error(
            `invalid category '${category}'.\n` +
            `available categories: ${categoriasLista}`
        );
    }
    
    const regexCategory = new RegExp(`^${normalizedCategory}$`, 'i');
    
    const movies = await db.collection('movies')
        .find({ genres: regexCategory })
        .limit(50) 
        .toArray();
        
    return movies.map(sanitizeMovie);
}