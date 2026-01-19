import os
import sqlite3
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)

# =========================
# CARREGAR VARIÁVEIS DE AMBIENTE
# =========================
load_dotenv()
TOKEN = os.environ.get("TELEGRAM_TOKEN")
DB_PATH = "financeiro.db"

# =========================
# BANCO DE DADOS
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            valor REAL,
            descricao TEXT,
            categoria TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()

def adicionar_transacao(user_id, valor, descricao, categoria):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    data = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        "INSERT INTO transacoes (user_id, valor, descricao, categoria, data) VALUES (?, ?, ?, ?, ?)",
        (user_id, valor, descricao, categoria, data)
    )
    conn.commit()
    conn.close()

def obter_relatorio_mes(user_id, mes=None, ano=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hoje = datetime.now()
    mes = mes or hoje.month
    ano = ano or hoje.year
    c.execute("""
        SELECT categoria, SUM(valor)
        FROM transacoes
        WHERE user_id = ? AND strftime('%m', data) = ? AND strftime('%Y', data) = ?
        GROUP BY categoria
    """, (user_id, f"{mes:02d}", str(ano)))
    resultado = c.fetchall()
    conn.close()
    return resultado

# =========================
# FLASK APP PARA WEBHOOK
# =========================
app = Flask(__name__)
bot = Bot(TOKEN)

# =========================
# MENU DE BOTÕES
# =========================
def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Adicionar Receita", callback_data='adicionar')],
        [InlineKeyboardButton("📊 Relatório Mensal", callback_data='relatorio')]
    ])

# =========================
# COMANDOS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Bem-vindo ao Bot Financeiro! Escolha uma opção:",
        reply_markup=menu_keyboard()
    )

# =========================
# CALLBACK DOS BOTÕES
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'adicionar':
        await query.edit_message_text(
            "Envie a transação no formato:\n`valor;descricao;categoria`",
            parse_mode="Markdown"
        )
        context.user_data['esperando_transacao'] = True

    elif query.data == 'relatorio':
        relatorio = obter_relatorio_mes(user_id)
        if not relatorio:
            texto = "Nenhuma transação registrada este mês."
        else:
            texto = "📊 Relatório do mês:\n"
            for categoria, total in relatorio:
                texto += f"{categoria}: R$ {total:.2f}\n"
        await query.edit_message_text(texto, reply_markup=menu_keyboard())

# =========================
# RECEBER MENSAGENS
# =========================
async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if context.user_data.get('esperando_transacao'):
        texto = update.message.text
        try:
            partes = [x.strip() for x in texto.split(";")]
            if len(partes) != 3:
                raise ValueError("Formato inválido")
            valor = float(partes[0].replace(",", "."))
            descricao = partes[1]
            categoria = partes[2]
            adicionar_transacao(user_id, valor, descricao, categoria)
            await update.message.reply_text(
                f"✅ Transação adicionada: {descricao} - R$ {valor:.2f} ({categoria})",
                reply_markup=menu_keyboard()
            )
        except:
            await update.message.reply_text(
                "❌ Formato inválido! Use `valor;descricao;categoria`",
                reply_markup=menu_keyboard()
            )
        context.user_data['esperando_transacao'] = False
    else:
        await update.message.reply_text(
            "Use os botões para interagir com o bot (/start).",
            reply_markup=menu_keyboard()
        )

# =========================
# CONFIGURAR TELEGRAM APPLICATION
# =========================
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem))

# =========================
# ROTA WEBHOOK
# =========================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return "ok"

# =========================
# RODAR BOT LOCAL (para testes)
# =========================
if __name__ == "__main__":
    init_db()
    print("Bot rodando...")
    application.run_polling()
