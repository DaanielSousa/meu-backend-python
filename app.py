import os
import sqlite3
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)

# 1. CHAVE INTERNA (Pode deixar essa frase ou inventar uma nova)
app.secret_key = "faturamento_secreto_da_nefrologia_2026_daniel"

# 2. CONFIGURAÇÃO DO GOOGLE (OAuth)
# Certifique-se de que o ID termina em .apps.googleusercontent.com
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

# --- FUNÇÕES DO BANCO DE DADOS (SQLite) ---
def conectar_bd():
    return sqlite3.connect('tarefas.db')

def init_db():
    with conectar_bd() as conn:
        # Tabela para as tarefas enviadas pela extensão
        conn.execute('''CREATE TABLE IF NOT EXISTS tarefas 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, tarefa TEXT, data TEXT)''')
        # Tabela para a "Lista Branca" de usuários autorizados (Opção A)
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE)''')
        
        # ADICIONE SEU E-MAIL REAL AQUI
        meu_email = 'daanielsousa2@gmail.com' 
        conn.execute('INSERT OR IGNORE INTO usuarios (email) VALUES (?)', (meu_email,))
        conn.commit()

# Inicializa o banco ao rodar o app
init_db()

# --- ROTAS DE ACESSO E LOGIN ---

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('painel'))
    return render_template('login.html')

@app.route('/login')
def login():
    # O redirect_uri deve ser EXATAMENTE igual ao que você colou no Google Cloud
    redirect_uri = url_for('auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/callback')
def auth():
    token = google.authorize_access_token()
    # Busca os dados do usuário que acabou de logar
    resp = google.get('https://www.googleapis.com/oauth2/v1/userinfo')
    user_info = resp.json()
    email = user_info.get('email')

    # Verifica se o e-mail está na nossa tabela de permitidos
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM usuarios WHERE email = ?', (email,))
        usuario_autorizado = cursor.fetchone()

    if usuario_autorizado:
        session['user'] = email
        return redirect(url_for('painel'))
    else:
        return f"Acesso Negado! O e-mail {email} não tem permissão para acessar este sistema.", 403

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- PAINEL PRINCIPAL (SÓ ACESSA LOGADO) ---

@app.route('/painel')
def painel():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('index.html', user_email=session['user'])

# --- API PARA A EXTENSÃO E PARA O SITE ---

@app.route('/salvar', methods=['POST'])
def salvar():
    # Esta rota fica aberta para a extensão conseguir enviar dados
    dados = request.json
    tarefa = dados.get('tarefa')
    data = dados.get('data')
    if tarefa and data:
        with conectar_bd() as conn:
            conn.execute('INSERT INTO tarefas (tarefa, data) VALUES (?, ?)', (tarefa, data))
            conn.commit()
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro", "mensagem": "Dados incompletos"}), 400

@app.route('/listar', methods=['GET'])
def listar():
    # Só permite listar se estiver logado no navegador
    if 'user' not in session:
        return jsonify({"erro": "Não autorizado"}), 401
        
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT tarefa, data FROM tarefas ORDER BY id DESC')
        tarefas = cursor.fetchall()
    
    # Formata os dados para o JavaScript do painel ler
    lista_tarefas = [{"tarefa": t[0], "data": t[1]} for t in tarefas]
    return jsonify(lista_tarefas)

if __name__ == '__main__':
    # Em produção (Render), o Gunicorn ignora esta linha, mas é bom para teste local
    app.run(debug=True)
