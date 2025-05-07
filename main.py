import logging
import os
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Token do bot (substitua pela sua variável de ambiente)
TOKEN = os.getenv("BOT_TOKEN")

# ID do grupo para enviar mensagens automáticas
GROUP_CHAT_ID = -4788783750

# Saldo inicial
saldo = 0.0

# Lista de transações
transacoes = []

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Olá! Sou o bot para registrar suas finanças. Use /entrada, /saida, /saldo, /listar, /relatorio, /limpar e /ajuda para mais informações.")

# Comando /entrada
async def entrada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global saldo
    try:
        valor = float(context.args[0])
        descricao = ' '.join(context.args[1:]) if len(context.args) > 1 else 'Entrada'
        saldo += valor
        transacoes.append(('entrada', valor, descricao, datetime.now()))
        await update.message.reply_text(f'Entrada de R${valor:.2f} registrada. Saldo atual: R${saldo:.2f}')
    except (IndexError, ValueError):
        await update.message.reply_text('Uso correto: /entrada valor descrição(opcional)')

# Comando /saida
async def saida(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global saldo
    try:
        valor = float(context.args[0])
        descricao = ' '.join(context.args[1:]) if len(context.args) > 1 else 'Saída'
        saldo -= valor
        transacoes.append(('saida', valor, descricao, datetime.now()))
        await update.message.reply_text(f'Saída de R${valor:.2f} registrada. Saldo atual: R${saldo:.2f}')
    except (IndexError, ValueError):
        await update.message.reply_text('Uso correto: /saida valor descrição(opcional)')

# Comando /saldo
async def saldo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Saldo atual: R${saldo:.2f}')

# Comando /listar
async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not transacoes:
        await update.message.reply_text("Nenhuma transação registrada.")
    else:
        msg = "Lista de transações:\n"
        for transacao in transacoes:
            tipo, valor, descricao, data = transacao
            msg += f"{data.strftime('%d/%m/%Y %H:%M:%S')} - {tipo.capitalize()}: R${valor:.2f} - {descricao}\n"
        await update.message.reply_text(msg)

# Comando /relatorio
async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    relatorio = gerar_relatorio()
    await update.message.reply_text(relatorio, parse_mode='Markdown')

# Função para gerar relatório mensal
def gerar_relatorio():
    entradas = sum(v for t, v, _, _ in transacoes if t == 'entrada')
    saidas = sum(v for t, v, _, _ in transacoes if t == 'saida')
    saldo_final = entradas - saidas
    relatorio = (
        f"📊 *Relatório Financeiro do Mês*\n\n"
        f"💰 Entradas: R${entradas:.2f}\n"
        f"💸 Saídas: R${saidas:.2f}\n"
        f"🧾 Saldo final: R${saldo_final:.2f}"
    )
    return relatorio

# Comando /limpar
async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global transacoes, saldo
    transacoes = []
    saldo = 0.0
    await update.message.reply_text("Todas as transações e o saldo foram limpos.")

# Comando /ajuda
async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ajuda_msg = (
        "Comandos disponíveis:\n\n"
        "/start - Inicia o bot e exibe informações básicas\n"
        "/entrada <valor> <descrição(opcional)> - Registra uma entrada de dinheiro\n"
        "/saida <valor> <descrição(opcional)> - Registra uma saída de dinheiro\n"
        "/saldo - Exibe o saldo atual\n"
        "/listar - Exibe todas as transações registradas\n"
        "/relatorio - Gera o relatório financeiro do mês\n"
        "/limpar - Limpa todas as transações e zera o saldo\n"
        "/ajuda - Exibe este menu de ajuda"
    )
    await update.message.reply_text(ajuda_msg)

# Tarefa agendada
async def tarefa_agendada(context: ContextTypes.DEFAULT_TYPE):
    relatorio = gerar_relatorio()
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=relatorio, parse_mode='Markdown')

# Função principal
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("entrada", entrada))
    app.add_handler(CommandHandler("saida", saida))
    app.add_handler(CommandHandler("saldo", saldo_cmd))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("relatorio", relatorio))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CommandHandler("ajuda", ajuda))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        tarefa_agendada,
        CronTrigger(day="5", hour=9, minute=0),
        args=[app.bot],
    )
    scheduler.start()

    print("Bot rodando...")
    await app.run_polling()

# Inicializa nest_asyncio e roda o bot
if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
