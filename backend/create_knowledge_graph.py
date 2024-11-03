import os
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_community.graphs.graph_document import Node, Relationship
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModel

from dotenv import load_dotenv
load_dotenv()

MODEL = "mixtral-8x7b-32768"
DOCS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

# Create the LLM
os.environ["OPENAI_API_KEY"] = os.environ.get("GROQ_API_KEY")
llm = ChatOpenAI(
    model="mixtral-8x7b-32768",
    temperature=0,
    openai_api_base=GROQ_API_BASE
)


# Create the Embedding model
model_name = "sentence-transformers/msmarco-distilbert-base-tas-b"
embedding_provider = HuggingFaceEmbeddings(model_name=model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token  

# Create instance of Graph
graph = Neo4jGraph(
    url=os.getenv('NEO4J_URI'),
    username=os.getenv('NEO4J_USERNAME'),
    password=os.getenv('NEO4J_PASSWORD')
)

# Create the LLM Graph Transformer: The LLMGraphTransformer converts 
# text documents into structured graph documents by leveraging a LLM to parse and 
# categorize entities and their relationships. 
# https://python.langchain.com/v0.1/docs/use_cases/graph/constructing/#llm-graph-transformer
doc_transformer = LLMGraphTransformer(
    llm=llm,
    ignore_tool_usage=True,
)

# 1. Gather the data
loader = DirectoryLoader(DOCS_PATH, glob="**/*.pdf", loader_cls=PyPDFLoader)
docs = loader.load()

# 2. Split the data into chunks
text_splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=1500,
    chunk_overlap=200,
)

chunks = text_splitter.split_documents(docs)

# 3. Vectorize Data: Create embeddings for each chunk
for chunk in chunks:
    filename = os.path.basename(chunk.metadata["source"])
    page = chunk.metadata["page"]
    chunk_id = f"{filename}.{page}"
    print("Processing -", chunk_id)

    # Embed the chunk text content
    chunk_embedding = embedding_provider.embed_query(chunk.page_content)

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
    graph.query("""
        MERGE (d:Document {id: $filename})
        MERGE (c:Chunk {id: $chunk_id})
        SET c.text = $text
        MERGE (d)<-[:PART_OF]-(c)
        WITH c
        CALL db.create.setNodeVectorProperty(c, 'textEmbedding', $embedding)
        """, 
        properties
    )

    # 4. Generate the entities and relationships from the chunk with LLM (converts text to graph entities and relationships)
    graph_docs = doc_transformer.convert_to_graph_documents([chunk])

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

    # 5. add the graph documents to the graph
    graph.add_graph_documents(graph_docs)

# 6. Create the vector index to query the chunks by their text embeddings
graph.query("""
    CREATE VECTOR INDEX `chunkVector`
    IF NOT EXISTS
    FOR (c: Chunk) ON (c.textEmbedding)
    OPTIONS {indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
    }};""")
