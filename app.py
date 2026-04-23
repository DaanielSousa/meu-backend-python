import os
import sqlite3
import holidays
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cbn_faturamento_segredo_2026"

CORS(app)

def conectar_bd():
    return sqlite3.connect('tarefas.db')

def init_db():
    with conectar_bd() as conn:
        # Tabela de Tarefas
        conn.execute('''CREATE TABLE IF NOT EXISTS tarefas 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, tarefa TEXT, data TEXT, status INTEGER DEFAULT 0, autor TEXT, responsavel_id INTEGER)''')
        # Tabela de Equipe (Login Interno)
        conn.execute('''CREATE TABLE IF NOT EXISTS equipe 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, whatsapp TEXT, senha TEXT)''')
        # Tabela de Médicos (Para cobrança recorrente)
        conn.execute('''CREATE TABLE IF NOT EXISTS medicos 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, crm TEXT, whatsapp TEXT)''')
        
        # Usuário Admin Inicial (Login: admin / Senha: 123)
        conn.execute('INSERT OR IGNORE INTO equipe (nome, email, whatsapp, senha) VALUES (?, ?, ?, ?)', 
                     ('Daniel Admin', 'admin', '61900000000', '123'))
        conn.commit()

init_db()

@app.route('/')
def home():
    if 'user' in session: return redirect(url_for('painel'))
    return render_template('login_local.html')

@app.route('/login', methods=['POST'])
def login():
    d = request.json
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('SELECT nome FROM equipe WHERE email = ? AND senha = ?', (d.get('email'), d.get('senha')))
        user = c.fetchone()
        if user:
            session['user'] = user[0]
            return jsonify({"status": "sucesso"})
    return jsonify({"status": "erro", "msg": "Usuário ou senha inválidos"}), 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/painel')
def painel():
    if 'user' not in session: return redirect(url_for('home'))
    return render_template('index_local.html', user_email=session['user'])

# --- MÓDULO DE TAREFAS ---
@app.route('/salvar', methods=['POST'])
def salvar():
    d = request.json
    with conectar_bd() as conn:
        conn.execute('INSERT INTO tarefas (tarefa, data, autor, responsavel_id) VALUES (?, ?, ?, ?)', 
                     (d['tarefa'], d['data'], session['user'], d['responsavel_id']))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/listar')
def listar():
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('''SELECT t.id, t.tarefa, t.data, t.status, t.autor, e.nome, e.whatsapp 
                  FROM tarefas t LEFT JOIN equipe e ON t.responsavel_id = e.id ORDER BY t.status ASC, t.id DESC''')
        return jsonify([{"id":t[0],"tarefa":t[1],"data":t[2],"status":t[3],"autor":t[4],"nome_resp":t[5],"zap_resp":t[6]} for t in c.fetchall()])

@app.route('/atualizar_status/<int:id>', methods=['POST'])
def atualizar_status(id):
    s = request.json.get('status')
    with conectar_bd() as conn:
        conn.execute('UPDATE tarefas SET status = ? WHERE id = ?', (s, id))
        conn.commit()
    return jsonify({"status": "sucesso"})

# --- MÓDULO DE MÉDICOS ---
@app.route('/cadastrar_medico', methods=['POST'])
def cadastrar_medico():
    d = request.json
    with conectar_bd() as conn:
        conn.execute('INSERT INTO medicos (nome, crm, whatsapp) VALUES (?, ?, ?)', (d['nome'], d['crm'], d['whatsapp']))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/listar_medicos')
def listar_medicos():
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('SELECT id, nome, crm, whatsapp FROM medicos')
        return jsonify([{"id":m[0],"nome":m[1],"crm":m[2],"zap":m[3]} for m in c.fetchall()])

# --- IA DE DATAS ---
@app.route('/verificar_data', methods=['POST'])
def verificar_data():
    data_str = request.json.get('data')
    dt = datetime.strptime(data_str, '%Y-%m-%dT%H:%M')
    br_holidays = holidays.BR()
    res = {"mensagem": ""}
    if dt.date() in br_holidays: res = {"mensagem": f"Atenção: Feriado ({br_holidays.get(dt.date())})"}
    elif dt.weekday() >= 5: res = {"mensagem": "Atenção: Final de semana."}
    return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True)