// codigo responsavel pelo CRUD e filtros do servidor XDR
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

// valida integridade dos metadados antes de tocar no banco
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

// higieniza documento do mongo para conformidade com contrato do protobuf
function sanitizeMovie(movie: any) {
    if (!movie) return null;
    
    return {
        ...movie,
        _id: movie._id.toString(),
        // forca conversao se motor entregar objeto de data nativo
        released: movie.released instanceof Date ? movie.released.toISOString() : (movie.released || ''),
        lastupdated: movie.lastupdated instanceof Date ? movie.lastupdated.toISOString() : (movie.lastupdated || '')
    };
}





// funcao para buscar filme por id
export async function readMovie(db: Db, movieId: string) {
    if (!movieId) throw new Error('movie id not provided');
    

    // converte string do protobuf para tipo nativo do mongo
    const objectId = new ObjectId(movieId);
    
    // executa busca na colecao movies
    const movie = await db.collection('movies').findOne({ _id: objectId });
    if (!movie) throw new Error('movie not found');
    
    // encapsula retorno em array para repeated do protobuf
    return [sanitizeMovie(movie)]; 
}




// funcao para listar filmes por ator
export async function listByActor(db: Db, actorName: string) {
    if (!actorName) throw new Error('actor name not provided');
    
    // busca filmes onde o array cast contem nome informado
    const movies = await db.collection('movies')
        .find({ cast: actorName })
        .limit(50) // limitador
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

    // valida integridade de metadados antes
    validateMetadata(movieData.type, movieData.genres);

    // remove chave de id do payload para mongo gerar automaticamente
    const { _id, ...dataToInsert } = movieData;
    
    const result = await db.collection('movies').insertOne(dataToInsert);
    if (!result.acknowledged) throw new Error('insert operation failed');
    
    // busca e retorna registro confirmando criacao
    const insertedMovie = await db.collection('movies').findOne({ _id: result.insertedId });
    return [sanitizeMovie(insertedMovie)];
}




// atualiza campos especificos de filme - isola defaults do protobuf
export async function updateMovie(db: Db, movieId: string, updateData: any) {
    if (!movieId) throw new Error('movie id not provided');
    if (!updateData) throw new Error('update data not provided');
    
    // valida integridade de metadados antes
    validateMetadata(updateData.type, updateData.genres);

    const objectId = new ObjectId(movieId);
    const { _id, ...rawUpdateData } = updateData;
    
    // constroi objeto com chaves sofreram mutacao
    const dataToUpdate: any = {};
    
    // validacao e higienizacao dos campos de texto
    if (rawUpdateData.title?.trim()) dataToUpdate.title = rawUpdateData.title.trim();
    if (rawUpdateData.type?.trim()) dataToUpdate.type = rawUpdateData.type.trim();
    if (rawUpdateData.plot?.trim()) dataToUpdate.plot = rawUpdateData.plot.trim();
    
    // validacao do ano
    if (rawUpdateData.year && rawUpdateData.year >= 1888) {
        dataToUpdate.year = rawUpdateData.year;
    }
    
    // validacao de arrays (elenco, direcao, generos)
    if (rawUpdateData.genres?.length > 0) dataToUpdate.genres = rawUpdateData.genres;
    if (rawUpdateData.cast?.length > 0) dataToUpdate.cast = rawUpdateData.cast;
    if (rawUpdateData.directors?.length > 0) dataToUpdate.directors = rawUpdateData.directors;
    
    // bloqueia ida ao banco se payload resultante for vazio
    if (Object.keys(dataToUpdate).length === 0) {
        throw new Error('no valid data provided for update');
    }
    
    // injeta campos isolados no operador de mutacao
    const result = await db.collection('movies').updateOne(
        { _id: objectId },
        { $set: dataToUpdate }
    );
    
    if (result.matchedCount === 0) throw new Error('movie not found for update');
    
    const updatedMovie = await db.collection('movies').findOne({ _id: objectId });
    return [sanitizeMovie(updatedMovie)];
}




// remove filme do banco
export async function deleteMovie(db: Db, movieId: string) {
    if (!movieId) throw new Error('movie id not provided');
    
    const objectId = new ObjectId(movieId);
    const result = await db.collection('movies').deleteOne({ _id: objectId });
    
    if (result.deletedCount === 0) throw new Error('movie not found for deletion');
    
    return [];
}


// lista filmes filtrando pela categoria exata e validada
export async function listByCategory(db: Db, category: string) {
    if (!category) throw new Error('category not provided');
    
    const normalizedCategory = category.toLowerCase().trim();

    // aborta operacao sem gastar rede ou cpu - fail-fast
    if (!validGenres.has(normalizedCategory)) {
        const categoriasLista = Array.from(validGenres).sort().join(', ');
        throw new Error(
            `invalid category '${category}'.\n` +
            `available categories: ${categoriasLista}`
        );
    }
    
    const regexCategory = new RegExp(`^${normalizedCategory}$`, 'i');
    
    // executa busca na colecao movies
    const movies = await db.collection('movies')
        .find({ genres: regexCategory })
        .limit(50) 
        .toArray();
        
    return movies.map(sanitizeMovie);
}