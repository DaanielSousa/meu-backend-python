from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app) # Permite que a extensão acesse o servidor

# --- CONFIGURAÇÃO DO BANCO DE DATOS ---
def init_db():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# --- ROTAS ---

@app.route('/salvar', methods=['POST'])
def salvar_tarefa():
    dados = request.json
    nome = dados.get('tarefa')
    data = dados.get('data')

    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tarefas (nome, data) VALUES (?, ?)', (nome, data))
    conn.commit()
    conn.close()

    print(f"✅ Tarefa '{nome}' salva no banco de dados!")
    return jsonify({"status": "sucesso"}), 201

@app.route('/listar', methods=['GET'])
def listar_tarefas():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nome, data FROM tarefas')
    tarefas = [{"tarefa": row[0], "data": row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(tarefas)

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)