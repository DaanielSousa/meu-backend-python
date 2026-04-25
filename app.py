import sqlite3
import holidays
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cbn_gestao_total_2026"
CORS(app)

def conectar_bd():
    return sqlite3.connect('tarefas.db')

def init_db():
    with conectar_bd() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tarefas 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, tarefa TEXT, data TEXT, 
                        status INTEGER DEFAULT 0, autor TEXT, responsavel_id INTEGER, setor TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS equipe 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, 
                        whatsapp TEXT, senha TEXT, nivel TEXT, setor TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS medicos 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, crm TEXT, whatsapp TEXT)''')
        
        # Migrações de segurança para colunas novas
        try: conn.execute('ALTER TABLE tarefas ADD COLUMN setor TEXT DEFAULT "Faturamento"')
        except: pass
        try: conn.execute('ALTER TABLE equipe ADD COLUMN setor TEXT DEFAULT "Faturamento"')
        except: pass

        # Criar Daniel Admin se não existir
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
        c.execute('SELECT nome, nivel, setor FROM equipe WHERE email = ? AND senha = ?', (d.get('email'), d.get('senha')))
        user = c.fetchone()
        if user:
            session['user'], session['nivel'], session['setor'] = user[0], user[1], user[2]
            return jsonify({"status": "sucesso"})
    return jsonify({"status": "erro", "msg": "Login inválido"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/painel')
def painel():
    if 'user' not in session: return redirect(url_for('home'))
    return render_template('index.html', user_nome=session['user'], nivel=session['nivel'], setor=session['setor'])

@app.route('/listar')
def listar():
    s_user, n_user = session.get('setor'), session.get('nivel')
    with conectar_bd() as conn:
        c = conn.cursor()
        if n_user == 'Admin':
            c.execute('''SELECT t.id, t.tarefa, t.data, t.status, t.autor, e.nome, e.whatsapp, t.setor 
                         FROM tarefas t LEFT JOIN equipe e ON t.responsavel_id = e.id 
                         ORDER BY t.status ASC, t.id DESC''')
        else:
            c.execute('''SELECT t.id, t.tarefa, t.data, t.status, t.autor, e.nome, e.whatsapp, t.setor 
                         FROM tarefas t LEFT JOIN equipe e ON t.responsavel_id = e.id 
                         WHERE t.setor = ? ORDER BY t.status ASC, t.id DESC''', (s_user,))
        return jsonify([{"id":t[0],"tarefa":t[1],"data":t[2],"status":t[3],"autor":t[4],"nome_resp":t[5],"zap_resp":t[6],"setor":t[7]} for t in c.fetchall()])

@app.route('/salvar', methods=['POST'])
def salvar():
    d = request.json
    with conectar_bd() as conn:
        conn.execute('INSERT INTO tarefas (tarefa, data, autor, responsavel_id, setor) VALUES (?, ?, ?, ?, ?)', 
                     (d['tarefa'], d['data'], session['user'], d['responsavel_id'], session['setor']))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/cadastrar_equipe', methods=['POST'])
def cadastrar_equipe():
    if session.get('nivel') != 'Admin': return jsonify({"status":"erro"}), 403
    d = request.json
    with conectar_bd() as conn:
        conn.execute('INSERT INTO equipe (nome, email, whatsapp, senha, nivel, setor) VALUES (?, ?, ?, ?, ?, ?)', 
                     (d['nome'], d['usuario'], d['whatsapp'], d['senha'], d['nivel'], d['setor']))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/listar_equipe_completa')
def listar_equipe_completa():
    s_user, n_user = session.get('setor'), session.get('nivel')
    with conectar_bd() as conn:
        c = conn.cursor()
        if n_user == 'Admin': c.execute('SELECT id, nome, whatsapp, nivel, setor FROM equipe')
        else: c.execute('SELECT id, nome, whatsapp, nivel, setor FROM equipe WHERE setor = ?', (s_user,))
        return jsonify([{"id": e[0], "nome": e[1], "whatsapp": e[2], "nivel": e[3], "setor": e[4]} for e in c.fetchall()])

@app.route('/atualizar_status/<int:id>', methods=['POST'])
def atualizar_status(id):
    s = request.json.get('status')
    with conectar_bd() as conn:
        conn.execute('UPDATE tarefas SET status = ? WHERE id = ?', (s, id))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/deletar_equipe/<int:id>', methods=['DELETE'])
def deletar_equipe(id):
    if session.get('nivel') != 'Admin': return jsonify({"status":"erro"}), 403
    with conectar_bd() as conn:
        conn.execute('DELETE FROM equipe WHERE id = ?', (id,))
        conn.commit()
    return jsonify({"status": "sucesso"})

@app.route('/listar_medicos')
def listar_medicos():
    with conectar_bd() as conn:
        c = conn.cursor()
        c.execute('SELECT id, nome, crm, whatsapp FROM medicos')
        return jsonify([{"id":m[0],"nome":m[1],"crm":m[2],"zap":m[3]} for m in c.fetchall()])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
