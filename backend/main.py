from flask import Flask, request, jsonify
from app import App
from flask_cors import CORS
from create_knowledge_graph import KnowledgeGraphBuilder

chatbot = App()

app = Flask(__name__)
CORS(app)  # Esto habilita CORS para todas las rutas



# Endpoint para recibir queries del frontend
@app.route('/find_chunk', methods=['POST'])
def find_chunk_endpoint():
    print("SOLICITUD DE CHUNK")
    try:
        data = request.get_json()
        query = data.get("query")
        if query:
            answer = chatbot.answer_query(query)
            return jsonify({"answer": answer})
        else:
            return jsonify({"answer": "No se ingresó una consulta válida."}), 400
    except Exception as e:
        return jsonify({"answer": f"No se pudo responder la consulta. Error {e}"}), 400
    
    
# Endpoint para Crear grafo
@app.route('/create_kg', methods=['POST'])
def create_kg_endpoint():
    try: 
        chatbot.create_knowledge_graph()
        return jsonify({"response": "Grafo creado exitosamente"}), 200
    except Exception as e:
        return jsonify({"response": "No se pudo crear el grafo a partir del documento. Error: {e}"}), 400
        

if __name__ == '__main__':
    app.run(debug=True)
