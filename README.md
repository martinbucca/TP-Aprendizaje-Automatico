## Creacion del grafo Neo4j
1. Se cargan todos los documentos PDF que se encuentren en ./backend/documents
2. Se divide cada documento en chunks
3. A cada chunk se le calcula el vector embedding utilizando HuggingFace y el modelo sentence-transformers/msmarco-distilbert-base-tas-b (los embeddings tienen dimension 768).
4. Se crea un Nodo por cada documento que tiene como propiedades un id unico.
5. Se crea un Nodo por cada chunk que tiene como propiedades un id unico, el texto y el embedding.
6. Se crean relaciones entre cada chunk con el documento al que pertenece del tipo (Chunk)-PART_OF->(Document)
7. Utilizando LLMGraphTransformer (https://python.langchain.com/v0.1/docs/use_cases/graph/constructing/#llm-graph-transformer), se extraen entidades y relaciones por cada chunk y se agregan al grafo Neo4j. Cada entidad se relaciona con el chunk del cual fue extraida con una relacion del tipo (Chunk)-HAS_ENTITY->(Entity). Las entidades pueden tener relaciones entre sí dependiendo como la LLM haya decidido extraerlas/crearlas.
8. Se crea el Vector Index el cual va a ser consultado para buscar similitudes entre la query del usuario y los embeddings generados para cada chunk previamente. Se utiliza la funcion de similaridad Cosine.

## Vector Rag
1. Por cada pregunta/query ingresada por el usario se obtiene el embedding, utilizando el mismo proveedor de embeddings utilizado para crear los embeddings de los chunks de cada documento (HugginFace, modelo sentence-transformers/msmarco-distilbert-base-tas-b y una dimension de 768).
2. El Vector Index de Neo4j al recibir el embedding busca en su Indice por el top K de vectores mas cercanos. El top k es una constante setteada en 3, que puede ser modificada (NUMBER_OF_DOCUMENTS_RETRIEVED = 3).
3. Obtiene los chunks mas parecidos al embedding de la consulta del usuario, su puntaje de similitud y realiza una Retrieval Query que le permite expandir su contexto: Por cada chunk obtenido, busca en el grafo todas las entidades relacionadas a ese chunk y por cada entidad todas sus aristas/relaciones y devuelve todo eso como contexto.
4. Se le pasa a la LLM ChatGroq un prompt que tiene instrucciones especificas sobre que responder y el contexto obtenido del Vector Index en el paso 3. Se invoca a esta LLM y se devuelve el resultado. 
 

## Como correr
1. Activar virtual env:
```
cd backend
python3 -m venv venv
source venv/bin/activate
```
2. Instalar dependencias:
```
cd backend
pip install -r requirements.txt
```
3. Correr backend:
```
cd backend
python3 main.py
```
4. Correr frontend:
```
cd frontend
npm install
npm start
```
