import os
import sqlite3
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = "faturamento_secreto_da_nefrologia_2026_daniel"

app.config['GOOGLE_CLIENT_ID'] = '774732337954-g13r0dn7ercb1a8a2o602f0cckvqu06f.apps.googleusercontent.com'
app.config['GOOGLE_CLIENT_SECRET'] = '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'

CORS(app)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def conectar_bd():
    return sqlite3.connect('tarefas.db')

def init_db():
    with conectar_bd() as conn:
        # Se precisar resetar o banco, remova o '#' da linha abaixo:
        # conn.execute('DROP TABLE IF EXISTS tarefas') 
        
        conn.execute('''CREATE TABLE IF NOT EXISTS tarefas 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         tarefa TEXT, 
                         data TEXT, 
                         status INTEGER DEFAULT 0,
                         autor TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE)''')
        
        meu_email = 'daanielsousa2@gmail.com' 
        conn.execute('INSERT OR IGNORE INTO usuarios (email) VALUES (?)', (meu_email,))
        conn.commit()

init_db()

@app.route('/')
def home():
    if 'user' in session: return redirect(url_for('painel'))
    return render_template('login.html')

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True, _scheme='https')
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v1/userinfo')
    user_info = resp.json()
    email = user_info.get('email')
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            session['user'] = email
            return redirect(url_for('painel'))
    return "Acesso Negado!", 403

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/painel')
def painel():
    if 'user' not in session: return redirect(url_for('home'))
    return render_template('index.html', user_email=session['user'])

@app.route('/salvar', methods=['POST'])
def salvar():
    dados = request.json
    tarefa = dados.get('tarefa')
    data = dados.get('data')
    autor = session.get('user', 'Extensão')
    if tarefa and data:
        with conectar_bd() as conn:
            conn.execute('INSERT INTO tarefas (tarefa, data, autor) VALUES (?, ?, ?)', (tarefa, data, autor))
            conn.commit()
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 400

@app.route('/listar', methods=['GET'])
def listar():
    if 'user' not in session: return jsonify({"erro": "Não autorizado"}), 401
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, tarefa, data, status, autor FROM tarefas ORDER BY id DESC')
        tarefas = cursor.fetchall()
    return jsonify([{"id": t[0], "tarefa": t[1], "data": t[2], "status": t[3], "autor": t[4]} for t in tarefas])

@app.route('/atualizar_status/<int:id>', methods=['POST'])
def atualizar_status(id):
    if 'user' not in session: return jsonify({"erro": "Não autorizado"}), 401
    status = request.json.get('status')
    with conectar_bd() as conn:
        conn.execute('UPDATE tarefas SET status = ? WHERE id = ?', (status, id))
        conn.commit()
    return jsonify({"status": "sucesso"})

if __name__ == '__main__':
    app.run(debug=True)
