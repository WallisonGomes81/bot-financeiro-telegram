import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================
# CONFIGURAÇÕES
# =========================
TOKEN = os.environ.get("8596236102:AAGS6gAvqZy12oYVku4znan7koF20ZuJphs")  # Token do bot no Render (env variable)
DB_PATH = "financeiro.db"

# =========================
# BANCO DE DADOS
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tabela de transações
    c.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            valor REAL,
            descricao TEXT,
            categoria TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()

def adicionar_transacao(valor, descricao, categoria):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    data = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO transacoes (valor, descricao, categoria, data) VALUES (?, ?, ?, ?)",
              (valor, descricao, categoria, data))
    conn.commit()
    conn.close()

def obter_relatorio_mes(mes=None, ano=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if not mes or not ano:
        mes = datetime.now().month
        ano = datetime.now().year
    c.execute("""
        SELECT categoria, SUM(valor) 
        FROM transacoes 
        WHERE strftime('%m', data) = ? AND strftime('%Y', data) = ?
        GROUP BY categoria
    """, (f"{mes:02d}", str(ano)))
    resultado = c.fetchall()
    conn.close()
    return resultado

# =========================
# COMANDOS DO BOT
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Adicionar Receita", callback_data='adicionar')],
        [InlineKeyboardButton("📊 Relatório Mensal", callback_data='relatorio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Olá! Bem-vindo ao Bot Financeiro.", reply_markup=reply_markup)

# =========================
# CALLBACKS DOS BOTÕES
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'adicionar':
        await query.edit_message_text("Envie a transação no formato:\n`valor;descricao;categoria`", parse_mode="Markdown")
        context.user_data['esperando_transacao'] = True

    elif query.data == 'relatorio':
        relatorio = obter_relatorio_mes()
        if not relatorio:
            texto = "Nenhuma transação registrada este mês."
        else:
            texto = "📊 Relatório do mês:\n"
            for categoria, total in relatorio:
                texto += f"{categoria}: R$ {total:.2f}\n"
        await query.edit_message_text(texto)

# =========================
# RECEBER MENSAGENS
# =========================
async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('esperando_transacao'):
        texto = update.message.text
        try:
            valor, descricao, categoria = [x.strip() for x in texto.split(";")]
            valor = float(valor.replace(",", "."))
            adicionar_transacao(valor, descricao, categoria)
            await update.message.reply_text(f"✅ Transação adicionada: {descricao} - R$ {valor:.2f} ({categoria})")
        except:
            await update.message.reply_text("❌ Formato inválido! Use `valor;descricao;categoria`")
        context.user_data['esperando_transacao'] = False
    else:
        await update.message.reply_text("Use os botões para interagir com o bot (/start).")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    init_db()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(app.builder.message_handler(mensagem))
    
    print("Bot rodando...")
    app.run_polling()
