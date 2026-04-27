import sqlite3
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cbn_omni_erp_2026_secure"
CORS(app)

def conectar_bd():
    return sqlite3.connect('cbn_omni.db')

def init_db():
    with conectar_bd() as conn:
        # 1. Tabelas Base
        conn.execute('CREATE TABLE IF NOT EXISTS setores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS equipe 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, 
                        whatsapp TEXT, senha TEXT, nivel TEXT, setor TEXT)''')

        # 2. Tabela de Tarefas (Atualizada para o Robô de Cobrança e Cards)
        conn.execute('''CREATE TABLE IF NOT EXISTS tarefas 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        tarefa TEXT, 
                        data TEXT, 
                        status INTEGER DEFAULT 0, 
                        autor TEXT, 
                        zap_autor TEXT, 
                        responsavel_id INTEGER, 
                        setor TEXT,
                        prioridade TEXT DEFAULT 'Média',
                        ultima_cobranca TEXT)''')

        # 3. Tabela de Médicos
        conn.execute('''CREATE TABLE IF NOT EXISTS medicos
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, whatsapp TEXT)''')

        # 4. Dados Iniciais: Setores
        setores = ['Faturamento', 'Financeiro', 'RH', 'Recepção', 'TI']
        for s in setores:
            conn.execute('INSERT OR IGNORE INTO setores (nome) VALUES (?)', (s,))

        # 5. Dados Iniciais: Usuário Admin Mestre
        conn.execute('''INSERT OR IGNORE INTO equipe (nome, email, whatsapp, senha, nivel, setor) 
                        VALUES (?, ?, ?, ?, ?, ?)''', 
                     ('Daniel Admin', 'admin', '61900000000', '123', 'Admin', 'Faturamento'))
        
        conn.commit()

init_db()

@app.route('/')
def home():
    if 'user' in session: return redirect(url_for('painel'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    d = request.json
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('SELECT nome, nivel, setor, whatsapp FROM equipe WHERE email = ? AND senha = ?', (d.get('email'), d.get('senha')))
        user = c.fetchone()
        if user:
            session['user'], session['nivel'], session['setor'], session['whatsapp'] = user[0], user[1], user[2], user[3]
            return jsonify({"status": "sucesso"})
    return jsonify({"status": "erro"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/painel')
def painel():
    if 'user' not in session: return redirect(url_for('home'))
    return render_template('index.html', user_nome=session['user'], nivel=session['nivel'], setor=session['setor'])

# --- MÓDULO DE TAREFAS E MONITORAMENTO ---

@app.route('/listar_tarefas')
def listar_tarefas():
    s_user, n_user = session.get('setor'), session.get('nivel')
    with conectar_bd() as conn:
        c = conn.cursor()
        # Buscamos agora t.zap_autor e t.prioridade para alimentar os cards
        query_base = '''SELECT t.id, t.tarefa, t.data, t.status, t.autor, e.nome, t.zap_autor, t.prioridade, t.setor 
                        FROM tarefas t LEFT JOIN equipe e ON t.responsavel_id = e.id '''
        
        if n_user == 'Admin':
            c.execute(query_base + 'ORDER BY t.status ASC, t.id DESC')
        else:
            c.execute(query_base + 'WHERE t.setor = ? ORDER BY t.status ASC, t.id DESC', (s_user,))
        
        return jsonify([{"id":t[0],"tarefa":t[1],"data":t[2],"status":t[3],"autor":t[4],
                         "nome_resp":t[5],"zap_autor":t[6], "prioridade":t[7], "setor":t[8]} for t in c.fetchall()])

@app.route('/salvar_tarefa', methods=['POST'])
def salvar_tarefa():
    d = request.json
    with conectar_bd() as conn:
        conn.execute('''INSERT INTO tarefas (tarefa, data, autor, zap_autor, responsavel_id, setor, prioridade) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                     (d['tarefa'], d['data'], session['user'], session.get('whatsapp'), 
                      d['responsavel_id'], session['setor'], d.get('prioridade', 'Média')))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/status_tarefa/<int:id>', methods=['POST'])
def status_tarefa(id):
    s = request.json.get('status')
    with conectar_bd() as conn:
        conn.execute('UPDATE tarefas SET status = ? WHERE id = ?', (s, id))
        conn.commit()
    return jsonify({"status": "sucesso"})

# --- MÓDULO DE GESTÃO DE EQUIPE ---

@app.route('/cadastrar_equipe', methods=['POST'])
def cadastrar_equipe():
    if session.get('nivel') != 'Admin':
        return jsonify({"status":"erro", "msg": "Acesso Negado"}), 403
    d = request.json
    with conectar_bd() as conn:
        conn.execute('INSERT INTO equipe (nome, email, whatsapp, senha, nivel, setor) VALUES (?, ?, ?, ?, ?, ?)', 
                     (d['nome'], d['usuario'], d['whatsapp'], d['senha'], d['nivel'], d['setor']))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/listar_equipe')
def listar_equipe():
    s_user, n_user = session.get('setor'), session.get('nivel')
    with conectar_bd() as conn:
        c = conn.cursor()
        if n_user == 'Admin': c.execute('SELECT id, nome, setor, nivel FROM equipe')
        else: c.execute('SELECT id, nome, setor, nivel FROM equipe WHERE setor = ?', (s_user,))
        return jsonify([{"id":e[0],"nome":e[1],"setor":e[2], "nivel":e[3]} for e in c.fetchall()])

@app.route('/deletar_equipe/<int:id>', methods=['DELETE'])
def deletar_equipe(id):
    if session.get('nivel') != 'Admin': return jsonify({"status":"erro"}), 403
    with conectar_bd() as conn:
        conn.execute('DELETE FROM equipe WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"status": "sucesso"})

# --- MÓDULO DE MÉDICOS E SETORES ---

@app.route('/listar_setores')
def listar_setores():
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('SELECT nome FROM setores')
        return jsonify([s[0] for s in c.fetchall()])

@app.route('/cadastrar_medico', methods=['POST'])
def cadastrar_medico():
    d = request.json
    with conectar_bd() as conn:
        conn.execute('INSERT INTO medicos (nome, whatsapp) VALUES (?, ?)', (d['nome'], d['whatsapp']))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/listar_medicos')
def listar_medicos():
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('SELECT nome, whatsapp FROM medicos')
        return jsonify([{"nome":m[0],"zap":m[1]} for m in c.fetchall()])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
