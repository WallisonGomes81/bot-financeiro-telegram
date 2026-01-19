from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import sqlite3
import datetime

DB_PATH = "financeiro.db"

# ===== Banco de dados =====
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ===== Menu inicial =====
def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Saldo", callback_data="saldo")],
        [InlineKeyboardButton("➕ Entrada", callback_data="entrada")],
        [InlineKeyboardButton("➖ Saída", callback_data="saida")],
        [InlineKeyboardButton("📊 Relatório mês atual", callback_data="relatorio")],
        [InlineKeyboardButton("📅 Relatório mês específico", callback_data="relatorio_mes")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Eu sou seu bot de controle financeiro.\nEscolha uma opção:",
        reply_markup=menu_keyboard()
    )

# ===== Botões =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "saldo":
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT valor FROM saldo WHERE id=1")
        saldo = cursor.fetchone()["valor"]
        db.close()
        await query.edit_message_text(f"💰 Saldo atual: R$ {saldo:.2f}", reply_markup=menu_keyboard())

    elif data in ["entrada", "saida"]:
        context.user_data["acao"] = data
        await query.edit_message_text(
            f"Digite o valor e descrição para {data} separados por espaço, ex: `100 Venda`",
            parse_mode='Markdown'
        )

    elif data == "relatorio":
        await gerar_relatorio(query, mes_atual=True)

    elif data == "relatorio_mes":
        context.user_data["relatorio_especifico"] = True
        await query.edit_message_text(
            "Digite o mês e ano no formato MM AAAA, ex: 01 2026"
        )

# ===== Função para gerar relatório =====
async def gerar_relatorio(query, mes_atual=False, mes=None, ano=None):
    db = get_db()
    cursor = db.cursor()

    if mes_atual:
        hoje = datetime.date.today()
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia = hoje
        titulo = f"📊 Relatório do mês {hoje.strftime('%m/%Y')}"
    else:
        primeiro_dia_mes = f"{ano}-{mes:02d}-01"
        if mes == 12:
            ultimo_dia = f"{ano}-12-31"
        else:
            ultimo_dia = f"{ano}-{mes+1:02d}-01"
        titulo = f"📊 Relatório de {mes:02d}/{ano}"

    cursor.execute("""
        SELECT tipo, SUM(valor) as total
        FROM movimentacoes
        WHERE date(data) >= ? AND date(data) < ?
        GROUP BY tipo
    """, (primeiro_dia_mes, ultimo_dia))
    resultados = cursor.fetchall()
    db.close()

    entrada = 0
    saida = 0
    for row in resultados:
        if row["tipo"] == "entrada":
            entrada = row["total"]
        elif row["tipo"] == "saida":
            saida = row["total"]

    saldo_periodo = entrada - saida
    mensagem = f"{titulo}:\nEntradas: R$ {entrada:.2f}\nSaídas: R$ {saida:.2f}\nSaldo: R$ {saldo_periodo:.2f}"
    await query.edit_message_text(mensagem, reply_markup=menu_keyboard())

# ===== Receber mensagem do usuário =====
async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    cursor = db.cursor()

    # Relatório mês específico
    if context.user_data.get("relatorio_especifico"):
        try:
            mes, ano = map(int, update.message.text.split())
            await gerar_relatorio(update.message, mes_atual=False, mes=mes, ano=ano)
        except:
            await update.message.reply_text("Formato inválido. Use MM AAAA, ex: 01 2026")
        context.user_data.pop("relatorio_especifico")
        return

    # Entrada ou saída
    acao = context.user_data.get("acao")
    if acao in ["entrada", "saida"]:
        try:
            partes = update.message.text.split()
            valor = float(partes[0])
            descricao = " ".join(partes[1:]) if len(partes) > 1 else acao.capitalize()

            # Pergunta confirmação
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmar", callback_data=f"confirma_{acao}_{valor}_{descricao}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]
            ])
            await update.message.reply_text(f"Confirme {acao}: R$ {valor:.2f} - {descricao}", reply_markup=keyboard)
        except:
            await update.message.reply_text("Formato inválido. Exemplo: 100 Venda")
        return

# ===== Confirmar entrada/saída =====
async def confirma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("confirma_"):
        _, acao, valor, descricao = data.split("_", 3)
        valor = float(valor)
        db = get_db()
        cursor = db.cursor()
        if acao == "entrada":
            cursor.execute("INSERT INTO movimentacoes (tipo, valor, descricao) VALUES (?, ?, ?)", ("entrada", valor, descricao))
            cursor.execute("UPDATE saldo SET valor = valor + ? WHERE id=1", (valor,))
        else:
            cursor.execute("INSERT INTO movimentacoes (tipo, valor, descricao) VALUES (?, ?, ?)", ("saida", valor, descricao))
            cursor.execute("UPDATE saldo SET valor = valor - ? WHERE id=1", (valor,))
        db.commit()
        db.close()
        await query.edit_message_text(f"{acao.capitalize()} confirmada: R$ {valor:.2f} - {descricao}", reply_markup=menu_keyboard())

    elif data == "cancelar":
        await query.edit_message_text("Operação cancelada.", reply_markup=menu_keyboard())

    context.user_data.pop("acao", None)

# ===== Inicializar bot =====
app = ApplicationBuilder().token("8596236102:AAGS6gAvqZy12oYVku4znan7koF20ZuJphs").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(CallbackQueryHandler(confirma, pattern="confirma_.*|cancelar"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem))

app.run_polling()
