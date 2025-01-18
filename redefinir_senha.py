import secrets
import string
import sys
from werkzeug.security import generate_password_hash
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config

# Função para conectar ao banco de dados
def connect_db():
    try:
        conn = {
            'host': config('DB_HOST', default='localhost'),
            'user': config('DB_USER', default='root'),
            'password': config('DB_PASSWORD', default='senha_padrao'),
            'database': config('DB_NAME', default='dados_pedidos')
        }
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

# Função para gerar uma senha temporária aleatória (somente letras e números)
def gerar_senha_temporaria(tamanho=12):
    caracteres = string.ascii_letters + string.digits  # Apenas letras e números
    senha = ''.join(secrets.choice(caracteres) for i in range(tamanho))
    return senha

# Função para obter o e-mail do usuário a partir do banco de dados
def obter_email_usuario(user_id):
    try:
        conn = connect_db()
        if conn is None:
            raise Exception("Erro ao conectar ao banco de dados")

        cursor = conn.cursor()
        cursor.execute("SELECT email FROM usuarios WHERE id = %s", (user_id,))
        resultado = cursor.fetchone()

        if resultado:
            return resultado[0]  # Retorna o e-mail do usuário
        else:
            print("Usuário não encontrado.")
            return None
    except Exception as e:
        print(f"Erro ao buscar o e-mail do usuário: {e}")
        return None
    finally:
        # Garantir que o cursor e a conexão sejam fechados
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Função para atualizar a senha no banco de dados
def atualizar_senha_usuario(user_id, hash_senha):
    try:
        conn = connect_db()
        if conn is None:
            raise Exception("Erro ao conectar ao banco de dados")

        cursor = conn.cursor()

        # Atualize a senha do usuário no banco de dados
        cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (hash_senha, user_id))
        conn.commit()

    except Exception as e:
        print(f"Erro ao atualizar a senha: {e}")
    finally:
        # Garantir que o cursor e a conexão sejam fechados
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Função para obter o nome do usuário a partir do banco de dados
def obter_nome_usuario(user_id):
    try:
        conn = connect_db()
        if conn is None:
            raise Exception("Erro ao conectar ao banco de dados")

        cursor = conn.cursor()
        cursor.execute("SELECT nome, email FROM usuarios WHERE id = %s", (user_id,))
        resultado = cursor.fetchone()

        if resultado:
            return resultado[0], resultado[1]  # Retorna o nome e o e-mail do usuário
        else:
            print("Usuário não encontrado.")
            return None, None
    except Exception as e:
        print(f"Erro ao buscar o nome e e-mail do usuário: {e}")
        return None, None
    finally:
        # Garantir que o cursor e a conexão sejam fechados
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Função principal para redefinir a senha
def redefinir_senha(user_id):
    try:
        # Obter o nome e o e-mail do usuário a partir do banco de dados
        nome_usuario, usuario_email = obter_nome_usuario(user_id)
        if not usuario_email:
            print(f"Erro: Não foi possível encontrar o e-mail para o usuário com ID {user_id}.")
            return

        print(f"Gerando senha temporária para o usuário {user_id}")
        senha_temporaria = gerar_senha_temporaria()
        hash_senha = generate_password_hash(senha_temporaria)
        
        print(f"Atualizando senha do usuário {user_id}")
        atualizar_senha_usuario(user_id, hash_senha)

        print(f"Enviando e-mail para {usuario_email}")
        
        # Corpo do e-mail com o nome do usuário
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="width: 100%; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;">
                <h2 style="text-align: center; color: #4CAF50;">Sua Nova Senha Temporária</h2>
                <p style="font-size: 16px;">Olá, {nome_usuario},</p>
                <p style="font-size: 16px;">Sua nova senha temporária é:</p>
                <h3 style="text-align: center; color: #4CAF50;">{senha_temporaria}</h3>
                <p style="font-size: 16px;">Por favor, altere sua senha assim que possível, acessando sua conta.</p>
                <p style="font-size: 16px; color: #555;">Se você não solicitou esta alteração, entre em contato conosco imediatamente.</p>
                <footer style="margin-top: 20px; text-align: center; font-size: 14px; color: #aaa;">
                    <p>Atenciosamente,</p>
                    <p><strong>Equipe de Suporte</strong></p>
                </footer>
            </div>
        </body>
        </html>
        """
        
        enviar_email(usuario_email, senha_temporaria, corpo_html)  # Passando o corpo do e-mail atualizado

        print(f"Senha temporária gerada e e-mail enviado para {usuario_email}")
    except Exception as e:
        print(f"Erro ao redefinir a senha: {e}")

# Função para enviar o e-mail com a nova senha
def enviar_email(usuario_email, senha_temporaria, corpo_html):
    remetente = "suportehotalicas@gmail.com"
    destinatario = usuario_email
    assunto = "Sua Nova Senha Temporária"

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html'))  # Usando 'html' para enviar e-mail com HTML

    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)  # Substitua se necessário
        servidor.starttls()
        servidor.login("suportehortalicas@gmail.com", "nqzt irdv yvhj ztez")  # Substitua com sua senha de app
        text = msg.as_string()
        servidor.sendmail(remetente, destinatario, text)
        servidor.quit()
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar o e-mail: {e}")

# Função principal para redefinir a senha
def redefinir_senha(user_id):
    try:
        # Obter o e-mail do usuário a partir do banco de dados
        usuario_email = obter_email_usuario(user_id)
        if not usuario_email:
            print(f"Erro: Não foi possível encontrar o e-mail para o usuário com ID {user_id}.")
            return

        print(f"Gerando senha temporária para o usuário {user_id}")
        senha_temporaria = gerar_senha_temporaria()
        hash_senha = generate_password_hash(senha_temporaria)
        
        print(f"Atualizando senha do usuário {user_id}")
        atualizar_senha_usuario(user_id, hash_senha)

        print(f"Enviando e-mail para {usuario_email}")
        enviar_email(usuario_email, senha_temporaria)
        
        print(f"Senha temporária gerada e e-mail enviado para {usuario_email}")
    except Exception as e:
        print(f"Erro ao redefinir a senha: {e}")

# Verifique se o script foi chamado com um argumento
if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])  # Pega o ID do usuário do argumento passado
        redefinir_senha(user_id)  # Chama a função para redefinir a senha
    else:
        print("Erro: O ID do usuário não foi fornecido.")
