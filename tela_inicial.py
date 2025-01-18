from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required
import traceback
import subprocess
from decouple import config
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app.secret_key = config('SECRET_KEY', default='sua_chave_secreta') # Necessário para sessões
login_manager = LoginManager()
login_manager.init_app(app)

# Configuração do banco de dados MySQL
DATABASE_CONFIG = {
    'host': config('DB_HOST', default='localhost'),
    'user': config('DB_USER', default='root'),
    'password': config('DB_PASSWORD', default='senha_padrao'),
    'database': config('DB_NAME', default='dados_pedidos')
}

class User(UserMixin):
    def __init__(self, id, username, email, role_id):
        self.id = id
        self.username = username
        self.email = email
        self.role_id = role_id

    @classmethod
    def get(cls, user_id):
        # Aqui você faz a consulta ao banco para retornar o usuário baseado no ID
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, role_id FROM usuarios WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return cls(result[0], result[1], result[2], result[3])
            else:
                return None
        except Exception as e:
            logger.error(f"Erro ao carregar o usuário: {e}", exc_info=True)
            return None

# Defina como carregar o usuário com base no ID
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Função para conectar ao banco de dados
def connect_db():
    try:
        conn = mysql.connector.connect(
            host=DATABASE_CONFIG['host'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            database=DATABASE_CONFIG['database']
        )
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}", exec_info=True)
        traceback.print_exc()
        return None

@app.route('/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role_id != 1:  # Verificar se o usuário é Admin
        return jsonify({"error": "Acesso negado"}), 403

    try:
        # Adiciona um log para verificar se o subprocesso está sendo chamado corretamente
        logger.info(f"Chamando subprocesso para redefinir senha do usuário {user_id}")
        
        # Caminho para o script redefinir_senha.py
        script_path = r'C:\Users\pedro\OneDrive\Documentos\Projeto_Horta\redefinir_senha.py'

        # Chama o script via subprocess
        result = subprocess.run(
            ['python', script_path, str(user_id)],  # Passa o ID do usuário como argumento
            capture_output=True, text=True
        )
        
        # Verifica o resultado do subprocesso
        if result.returncode == 0:
            logger.info(f"Saída do subprocesso: {result.stdout}")
            return jsonify({"message": "Senha redefinida com sucesso!"})
        else:
            # Log de erro para depuração
            logger.error(f"Erro ao redefinir senha: {result.stderr}", exc_info=True)
            return jsonify({"error": f"Erro ao redefinir senha: {result.stderr}"}), 500

    except Exception as e:
        # Log de erro para depuração
        logger.error(f"Erro ao executar subprocesso: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role_id != 1:  # Verificar se o usuário é Admin
        return jsonify({"error": "Acesso negado"}), 403

    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Usuário excluído com sucesso!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    if 'user_id' in session:  # Verifica se o usuário está logado
        return redirect(url_for('home'))  # Redireciona para a página de pedidos
    return redirect(url_for('login'))  # Se não estiver logado, redireciona para a página de login

@app.route('/home', methods=['GET'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para login se não estiver logado

    # Acessando o ID e o nome do cliente armazenados na sessão
    user_id = session['user_id']
    nome_cliente = session.get('user_name')

    logger.info(f"Nome do cliente: {nome_cliente}")  # Teste para verificar se o nome está correto

    user_role = "Admin" if current_user.role_id == 1 else "Usuário"  # Verificação do papel
    logger.info(f"Role do usuário: {user_role}")  

    # Passar para o template
    return render_template('index.html', user_id=user_id, user_name=nome_cliente, role=user_role)

@app.route('/meu-endereco')
def minha_view():
    user = {
        'id': session.get('user_id'),
        'get_full_name': session.get('user_name')  # Ajuste conforme seu caso
    }
    return render_template('meu_template.html', user=user)

@app.route('/pedidos')
def pedidos_realizados():
    user_id = session['user_id']
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Verificar o papel do usuário
        cursor.execute("SELECT role_id FROM usuarios WHERE id = %s", (user_id,))  # Corrigido para 'id'
        role_id = cursor.fetchone()[0]

        if role_id == 1:  # Supondo que role_id = 1 é o papel de ADMIN
            # Se o usuário for ADMIN, pega todos os pedidos
            cursor.execute("SELECT nome_cliente, pedido, quantidade, data_pedido FROM pedidos")
        else:
            # Se não for ADMIN, pega apenas os pedidos do próprio usuário
            cursor.execute(
                "SELECT nome_cliente, pedido, quantidade, data_pedido FROM pedidos WHERE user_id = %s",
                (user_id,)
            )

        pedidos = cursor.fetchall()
        cursor.close()
        conn.close()

        # Garantir que data_pedido seja um objeto datetime
        pedidos_formatados = [
            {
                'nome_cliente': pedido[0],
                'pedido': pedido[1],
                'quantidade': pedido[2],
                'data_pedido': pedido[3].strftime("%d/%m/%Y %H:%M:%S") if isinstance(pedido[3], datetime) else datetime.strptime(pedido[3], '%Y-%m-%d %H:%M:%S').strftime("%d/%m/%Y %H:%M:%S"),
            }
            for pedido in pedidos
        ]

        return render_template('pedidos.html', pedidos=pedidos_formatados)

    except Exception as e:
        logger.error(f"Erro ao consultar os pedidos: {e}", exc_info=True)
        return "Erro no servidor", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')

        if not username_or_email or not password:
            flash("Por favor, preencha todos os campos.", 'error')
            return redirect(url_for('login'))
        
        try:
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute("SELECT id, username, password, role_id FROM usuarios WHERE username = %s OR email = %s", 
                           (username_or_email, username_or_email))
            user_data = cursor.fetchone()

            if user_data and check_password_hash(user_data[2], password):  # Verifica a senha
                user = User(user_data[0], user_data[1], user_data[2], user_data[3])  # Cria um objeto User
                login_user(user)  # Faz login do usuário

                session['user_id'] = user.id
                session['user_name'] = user.username

                return redirect(url_for('home'))
            else:
                flash("Nome de usuário ou senha incorretos.", 'error')
                return redirect(url_for('login'))

        except Exception as e:
            flash("Erro ao tentar autenticar. Tente novamente mais tarde.", 'error')
            return redirect(url_for('login'))
        
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

# Rota de realização de pedidos
@app.route('/realizar_pedido', methods=['GET','POST'])
def realizar_pedido():
    # Verificar se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para login se não estiver logado

    # Dados do formulário
    user_id = session['user_id']  # Confirmação do usuário autenticado
    nome_cliente = request.form.get('nome_cliente')  # Obtendo o nome correto do cliente
    itens = request.form.getlist('itens[]')  # Lista de itens selecionados

    logger.info(user_id, nome_cliente, itens)

    # Validação inicial
    if not nome_cliente or not itens:
        return "Dados incompletos no formulário", 400

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                # Remover "alface" da lista de itens
                if "alface" in itens:
                    itens = [item for item in itens if item != "alface"]  # Remover "alface"
                    logger.info(itens)  # Para verificar o resultado

                # Iterar sobre os itens restantes e inserir no banco de dados
                for item in itens:
                    quantidade = request.form.get(f'quantidade[{item}]')  # Quantidade de cada item

                    # Validação adicional de quantidade
                    if not quantidade or not quantidade.isdigit() or int(quantidade) <= 0:
                        return f"Quantidade inválida para o item {item}", 400
                    
                    # Inserir no banco de dados
                    cursor.execute(
                        'INSERT INTO pedidos (user_id, nome_cliente, pedido, quantidade) VALUES (%s, %s, %s, %s)',
                        (user_id, nome_cliente, item, int(quantidade))
                    )

            conn.commit()  # Confirmar transação

        # Redirecionar para a página de confirmação com o nome do cliente
        from urllib.parse import quote
        return redirect(url_for('confirmacao', nome=quote(nome_cliente)))

    except Exception as e:
        logger.error(f"Erro ao processar o pedido: {e}", exc_info=True)
        return f"Erro no servidor: {e}", 500

@app.route('/confirmacao')
def confirmacao():
    nome = request.args.get('nome')
    return render_template('confirmacao.html', nome=nome)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Verifica se as senhas coincidem
        if password != confirm_password:
            flash('As senhas não coincidem. Tente novamente.', 'error')
            return redirect(url_for('register'))

        # Hash da senha
        hashed_password = generate_password_hash(password)

        try:
            conn = connect_db()
            cursor = conn.cursor()

            # Verificar se o nome de usuário ou email já existem
            cursor.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Usuário ou email já cadastrado. Tente outro ou faça login.', 'error')
                return redirect(url_for('register'))

            # Inserir o novo usuário no banco de dados
            cursor.execute("INSERT INTO usuarios (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
            conn.commit()
            conn.close()

            return redirect(url_for('login'))  # Redireciona para a página de login

        except mysql.connector.Error as err:
            flash(f"Erro no banco de dados: {err}", 'error')
        except Exception as e:
            flash(f"Ocorreu um erro: {e}", 'error')

    return render_template('register.html')

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)  # Retorna os resultados como dicionários

        cursor.execute("""
            SELECT id, username, email,
                   CASE
                       WHEN role_id = 1 THEN 'Admin'
                       WHEN role_id = 2 THEN 'Usuário'
                       ELSE 'Desconhecido'
                   END AS role
            FROM usuarios
        """)
        usuarios = cursor.fetchall()
        return jsonify(usuarios)  # Converte automaticamente para JSON
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/usuarios')
@login_required
def usuarios():
    user_role = "Admin" if current_user.role_id == 1 else "Usuário"  # Verificação do papel
    logger.info(f"Role do usuário: {user_role}")  # Verifique se o valor está correto
    return render_template('usuarios.html', role=user_role)

if __name__ == '__main__':
    app.run()
