import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from collections import defaultdict

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ARQUIVO = "financas.json"

def carregar_dados():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, 'r') as f:
            return json.load(f)
    return {}

def salvar_dados(dados):
    with open(ARQUIVO, 'w') as f:
        json.dump(dados, f, indent=2)

def mes_atual():
    return datetime.now().strftime("%Y-%m")

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower()
    partes = texto.split()
    if len(partes) < 2:
        await update.message.reply_text("⚠️ Use: entrada/gasto valor categoria")
        return
    tipo, valor_txt = partes[0], partes[1]
    categoria = " ".join(partes[2:]) if len(partes) > 2 else "outros"
    try:
        valor = float(valor_txt.replace(",", "."))
    except:
        await update.message.reply_text("❌ Valor inválido.")
        return
    dados = carregar_dados()
    mes = mes_atual()
    if mes not in dados:
        dados[mes] = {"entradas": [], "saidas": []}
    registro = {"valor": valor, "categoria": categoria}
    if tipo == "entrada":
        dados[mes]["entradas"].append(registro)
        await update.message.reply_text(f"✅ Entrada de R$ {valor:.2f} registrada em '{categoria}'")
    elif tipo in ["gasto", "saida", "fatura"]:
        dados[mes]["saidas"].append(registro)
        await update.message.reply_text(f"❌ Saída de R$ {valor:.2f} registrada em '{categoria}'")
    else:
        await update.message.reply_text("⚠️ Use 'entrada', 'gasto' ou 'fatura'.")
    salvar_dados(dados)

def gerar_relatorio(mes=None):
    dados = carregar_dados()
    mes = mes or mes_atual()
    if mes not in dados:
        return f"📅 Nenhum dado encontrado para {mes}."
    entradas = dados[mes]["entradas"]
    saidas = dados[mes]["saidas"]
    def classificar(lista):
        soma_por_cat = defaultdict(float)
        total = 0.0
        for item in lista:
            soma_por_cat[item["categoria"]] += item["valor"]
            total += item["valor"]
        return soma_por_cat, total
    entradas_cat, total_entradas = classificar(entradas)
    saidas_cat, total_saidas = classificar(saidas)
    saldo = total_entradas - total_saidas
    def formatar(cat_dict, total):
        linhas = []
        for cat, val in cat_dict.items():
            pct = (val / total * 100) if total else 0
            linhas.append(f"- {cat}: R$ {val:.2f} ({pct:.2f}%)")
        return "\n".join(linhas)
    nome_mes = datetime.strptime(mes, "%Y-%m").strftime("%B %Y")
    relatorio = f"""📆 Mês: {nome_mes}

💰 Entradas (R$ {total_entradas:.2f}):
{formatar(entradas_cat, total_entradas)}

💸 Gastos (R$ {total_saidas:.2f}):
{formatar(saidas_cat, total_saidas)}

💼 Saldo final: R$ {saldo:.2f}"""
    return relatorio

async def relatorio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = gerar_relatorio()
    await update.message.reply_text(msg)

async def confirmar_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = gerar_relatorio()
    await update.message.reply_text(f"📊 Relatório confirmado!\n\n{msg}")

async def resetar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_dados({})
    await update.message.reply_text("🔄 Dados de todos os meses foram apagados.")

async def aviso_relatorio(context: ContextTypes.DEFAULT_TYPE):
    if CHAT_ID:
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text="📝 Já lançaram todos os gastos e entradas do mês anterior? Envie /confirmar_relatorio para gerar o relatório."
        )

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("relatorio", relatorio_cmd))
    app.add_handler(CommandHandler("confirmar_relatorio", confirmar_relatorio))
    app.add_handler(CommandHandler("resetar", resetar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar))
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Sao_Paulo"))
    scheduler.add_job(aviso_relatorio, "cron", day="1-10", hour=8, minute=0, args=[app.bot])
    scheduler.start()
    print("Bot rodando...")
    await app.run_polling()

import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise
