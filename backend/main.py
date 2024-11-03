from flask import Flask, request, jsonify
from vector_rag import find_chunk
from flask_cors import CORS


app = Flask(__name__)
CORS(app)  # Esto habilita CORS para todas las rutas



# Endpoint para recibir queries del frontend
@app.route('/find_chunk', methods=['POST'])
def find_chunk_endpoint():
    data = request.get_json()
    query = data.get("query")
    if query:
        answer = find_chunk(query)
        return jsonify({"answer": answer})
    else:
        return jsonify({"answer": "No se ingresó una consulta válida."}), 400

if __name__ == '__main__':
    app.run(debug=True)
