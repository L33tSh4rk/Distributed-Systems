// codigo responsavel por carregar o contrato protobuf
// autor: Allan


import protobuf from 'protobufjs';
import path from 'path';

// resolve caminho absoluto para evitar erros de execucao
const protoPath = path.resolve(__dirname, 'movies.proto');

// carrega o contrato de forma sincrona na inicializacao
const root = protobuf.loadSync(protoPath);

// extrai e exporta os envelopes principais
export const RequestPayload = root.lookupType('movies.RequestPayload');
export const ResponsePayload = root.lookupType('movies.ResponsePayload');