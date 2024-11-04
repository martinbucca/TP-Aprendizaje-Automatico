import os
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_experimental.graph_transformers.llm import default_prompt
from langchain_community.graphs.graph_document import Node, Relationship
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModel
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv
load_dotenv()

EMBEDDINGS_MODEL = "sentence-transformers/msmarco-distilbert-base-tas-b"
MODEL = "mixtral-8x7b-32768"
DOCS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

os.environ["OPENAI_API_KEY"] = os.environ.get("GROQ_API_KEY")

class KnowledgeGraphBuilder:
    def __init__(self):
        self.graph = Neo4jGraph(
            url=os.getenv('NEO4J_URI'),
            username=os.getenv('NEO4J_USERNAME'),
            password=os.getenv('NEO4J_PASSWORD')
        )
        self.llm = ChatOpenAI(
            model=MODEL,
            temperature=0,
            openai_api_base=GROQ_API_BASE
        )
        self.embedding_provider = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)
        self.docs_transformer = self.create_doc_transformer()        

    def create_doc_transformer(self):
        '''
        Create the LLM Graph Transformer: The LLMGraphTransformer converts 
        text documents into structured graph documents by leveraging a LLM to parse and 
        categorize entities and their relationships. 
        https://python.langchain.com/v0.1/docs/use_cases/graph/constructing/#llm-graph-transformer
        '''
        #graph_transformer_prompt = default_prompt + [
        #    ("human", "Importante: Las entidades y relaciones deben estar en el idioma Español.")
        #] 
        return LLMGraphTransformer(
            llm=self.llm,
            #prompt=graph_transformer_prompt,
            ignore_tool_usage=True,
        )   
        
    def empty_neo4j_database(self):
        self.graph.query("""
        MATCH (n)
        DETACH DELETE n;
        """
        )
        self.graph.query("""
        DROP INDEX chunkVector IF EXISTS;
        """
        )

    def add_entities_and_relationships(self, chunk, chunk_id):
        # Generate the entities and relationships from the chunk with LLM (converts text to graph entities and relationships)
        graph_docs = self.docs_transformer.convert_to_graph_documents([chunk])

        # Map the entities in the graph documents to the chunk node with a relationship HAS_ENTITY
        # going from the chunk node to the related entity nodes
        for graph_doc in graph_docs:
            chunk_node = Node(
                id=chunk_id,
                type="Chunk"
            )

            for node in graph_doc.nodes:

                graph_doc.relationships.append(
                    Relationship(
                        source=chunk_node,
                        target=node, 
                        type="HAS_ENTITY"
                        )
                    )

        # add the graph documents to the graph
        self.graph.add_graph_documents(graph_docs)


    def process_chunk(self, chunk):
        filename = os.path.basename(chunk.metadata["source"])
        page = chunk.metadata["page"]
        chunk_id = f"{filename}.{page}"
        print("Processing -", chunk_id)

        # Embed the chunk text content
        chunk_embedding = self.embedding_provider.embed_query(chunk.page_content)

        # Add the Document and Chunk nodes to the graph and set the text embedding property
        # Chunk -[:PART_OF]-> Document, where Document node has one single property: id (filename)
        # and Chunk node has three properties: id (chunk_id), text (chunk.page_content) and textEmbedding (chunk_embedding)
        properties = {
            "filename": filename,
            "chunk_id": chunk_id,
            "text": chunk.page_content,
            "embedding": chunk_embedding
        }
        
        # Add Nodes and Relationships to the graph
        self.graph.query("""
            MERGE (d:Document {id: $filename})
            MERGE (c:Chunk {id: $chunk_id})
            SET c.text = $text
            MERGE (d)<-[:PART_OF]-(c)
            WITH c
            CALL db.create.setNodeVectorProperty(c, 'textEmbedding', $embedding)
            """, 
            properties
        )

        self.add_entities_and_relationships(chunk, chunk_id)
        

    def create_vector_index(self):
        # Create the vector index to query the chunks by their text embeddings
        self.graph.query("""
            CREATE VECTOR INDEX `chunkVector`
            IF NOT EXISTS
            FOR (c: Chunk) ON (c.textEmbedding)
            OPTIONS {indexConfig: {
            `vector.dimensions`: 768,
            `vector.similarity_function`: 'cosine'
        }};""")


    def create_kg(self):
        try: 
            self.empty_neo4j_database()
            # Gather the data
            loader = DirectoryLoader(DOCS_PATH, glob="**/*.pdf", loader_cls=PyPDFLoader)
            docs = loader.load()
            # Split the data into chunks
            text_splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=1500,
                chunk_overlap=200,
            )

            chunks = text_splitter.split_documents(docs)
            # Vectorize Data: Create embeddings for each chunk
            for chunk in chunks:
                self.process_chunk(chunk)

            self.create_vector_index()
        except Exception as e:
            print(e)
            raise e

    





    
