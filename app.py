import sqlite3
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# CONFIGURAÇÃO DO BANCO DE DADOS
def init_db():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarefa TEXT NOT NULL,
            data TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Servidor Rodando com Sucesso!"

@app.route('/salvar', methods=['POST'])
def salvar():
    dados = request.json
    tarefa = dados.get('tarefa')
    data = dados.get('data')
    
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tarefas (tarefa, data) VALUES (?, ?)', (tarefa, data))
    conn.commit()
    conn.close()
    return jsonify({"status": "sucesso"}), 201

@app.route('/listar', methods=['GET'])
def listar():
    conn = sqlite3.connect('tarefas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tarefa, data FROM tarefas')
    tarefas = [{"tarefa": row[0], "data": row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(tarefas)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
