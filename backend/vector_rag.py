import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModel
from langchain_groq import ChatGroq


llm = ChatGroq(temperature=0,model_name="mixtral-8x7b-32768")

graph = Neo4jGraph(
    url=os.getenv('NEO4J_URI'),
    username=os.getenv('NEO4J_USERNAME'),
    password=os.getenv('NEO4J_PASSWORD')
)

# Create the Embedding model
model_name = "sentence-transformers/msmarco-distilbert-base-tas-b"
embedding_provider = HuggingFaceEmbeddings(model_name=model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token  

# Vector store for the chunks. This will be used to retrieve the most relevant chunk for a given question.
chunk_vector = Neo4jVector.from_existing_index(
    embedding_provider,
    graph=graph,
    # The name of the index created in the previous step
    index_name="chunkVector",
    # The name of the property in the node that contains the embeddings
    embedding_node_property="embedding",
    # The name of the property in the node that contains the text
    text_node_property="text",
    retrieval_query="""
// get the document
MATCH (node)-[:PART_OF]->(d:Document)
WITH node, score, d
// get the entities
MATCH (node)-[:HAS_ENTITY]-(e)
WITH node, score, d, collect(e) as nodeslist
// find the relationships between the entities related to the document
MATCH p = (e)-[r]-(e2)
WHERE e in nodeslist and e2 in nodeslist
// unwind the path, create a string of the entities and relationships
UNWIND relationships(p) as rels
WITH 
    node, 
    score, 
    d, 
    collect(apoc.text.join(
        [labels(startNode(rels))[0], startNode(rels).id, type(rels), labels(endNode(rels))[0], endNode(rels).id]
        ," ")) as kg
RETURN
    node.text as text, score,
    { 
        document: d.id,
        entities: kg
    } AS metadata
"""
)

instructions = (
    "Use the given context to answer the question."
    "Give FIUBA students the most accurate infromation about the double degree program as if you were a student advisor."
    "Answer what the student is asking, and give all the infromation possible from the text to support your answer."
    "If you don't know the answer, say you don't know."
    "Context: {context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", instructions),
        ("human", "{input}"),
    ]
)

chunk_retriever = chunk_vector.as_retriever()
chunk_chain = create_stuff_documents_chain(llm, prompt)
chunk_retriever = create_retrieval_chain(
    chunk_retriever, 
    chunk_chain
)

def find_chunk(q):
    print("Finding similarities for query: ", q)
    return chunk_retriever.invoke({"input": q})["answer"]



