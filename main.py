import logging
import os
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configurações de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ID do grupo
GROUP_CHAT_ID = -4788783750

# Carregar as credenciais do Google
creds = Credentials.from_service_account_file("credentials.json", scopes=["https://www.googleapis.com/auth/spreadsheets"])

# ID da planilha
SPREADSHEET_ID = 'sua-planilha-id'

# Função para autenticação com Google Sheets
def get_google_sheets_service():
    return build('sheets', 'v4', credentials=creds)

# Função para registrar entrada
async def entrada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        descricao = ' '.join(context.args[1:])
        # Aqui você faria a inserção no Google Sheets
        # Exemplo de lógica de inserção no Google Sheets
        service = get_google_sheets_service()
        sheet = service.spreadsheets()
        # Insere o valor da entrada na planilha
        sheet.values().append(spreadsheetId=SPREADSHEET_ID, range="Entradas!A1", valueInputOption="RAW", body={
            'values': [[valor, descricao]]
        }).execute()
        await update.message.reply_text(f"Entrada registrada: {valor} - {descricao}")
    except (IndexError, ValueError):
        await update.message.reply_text("Por favor, use o formato: /entrada <valor> <descrição>.")

# Função para registrar saída
async def saida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        descricao = ' '.join(context.args[1:])
        # Aqui você faria a inserção no Google Sheets
        # Exemplo de lógica de inserção no Google Sheets
        service = get_google_sheets_service()
        sheet = service.spreadsheets()
        # Insere o valor da saída na planilha
        sheet.values().append(spreadsheetId=SPREADSHEET_ID, range="Saídas!A1", valueInputOption="RAW", body={
            'values': [[valor, descricao]]
        }).execute()
        await update.message.reply_text(f"Saída registrada: {valor} - {descricao}")
    except (IndexError, ValueError):
        await update.message.reply_text("Por favor, use o formato: /saida <valor> <descrição>.")

# Função para calcular e retornar o saldo
async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Recupera os dados da planilha de entradas e saídas
        service = get_google_sheets_service()
        sheet = service.spreadsheets()
        
        # Obter entradas e saídas
        entradas = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Entradas!A:A").execute()
        saidas = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Saídas!A:A").execute()

        # Calcular o saldo
        total_entradas = sum(float(entry[0]) for entry in entradas.get('values', []))
        total_saidas = sum(float(entry[0]) for entry in saidas.get('values', []))
        saldo = total_entradas - total_saidas
        
        await update.message.reply_text(f"O saldo atual é: R${saldo:.2f}")
    except Exception as e:
        logger.error(f"Erro ao calcular saldo: {e}")
        await update.message.reply_text("Erro ao calcular o saldo.")

# Função para gerar o relatório
async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Obter as entradas e saídas
        service = get_google_sheets_service()
        sheet = service.spreadsheets()
        
        entradas = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Entradas!A:B").execute()
        saídas = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Saídas!A:B").execute()

        df_entradas = pd.DataFrame(entradas.get('values', []), columns=["Valor", "Descrição"])
        df_saidas = pd.DataFrame(saídas.get('values', []), columns=["Valor", "Descrição"])

        # Total de entradas e saídas
        total_entradas = df_entradas["Valor"].astype(float).sum()
        total_saidas = df_saidas["Valor"].astype(float).sum()

        # Envio do resumo
        relatorio_texto = f"Relatório do mês:\n\n"
        relatorio_texto += f"Total de Entradas: R${total_entradas:.2f}\n"
        relatorio_texto += f"Total de Saídas: R${total_saidas:.2f}\n"
        relatorio_texto += f"Saldo Final: R${total_entradas - total_saidas:.2f}"

        await update.message.reply_text(relatorio_texto)
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        await update.message.reply_text("Erro ao gerar o relatório.")

# Função para limpar registros
async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.text.lower() == '/limpar':
            await update.message.reply_text("Você tem certeza de que deseja apagar todos os registros? Responda com 'sim' ou 'não'.")
        else:
            if update.message.text.lower() == 'sim':
                service = get_google_sheets_service()
                sheet = service.spreadsheets()

                # Limpar entradas e saídas
                sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range="Entradas!A:B").execute()
                sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range="Saídas!A:B").execute()
                await update.message.reply_text("Registros apagados com sucesso.")
            else:
                await update.message.reply_text("Operação cancelada.")
    except Exception as e:
        logger.error(f"Erro ao limpar registros: {e}")
        await update.message.reply_text("Erro ao limpar os registros.")

# Função para mostrar os comandos de ajuda
async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comandos = """
    Comandos disponíveis:
    
    /entrada <valor> <descrição> - Registrar uma entrada (renda)
    /saida <valor> <descrição> - Registrar uma saída (gasto)
    /saldo - Verificar o saldo atual
    /relatorio - Gerar relatório com totais e percentuais
    /limpar - Apagar todos os registros (confirmar com 'sim')
    /ajuda - Exibir esta lista de comandos
    """
    await update.message.reply_text(comandos)

# Função principal para rodar o bot
def main():
    application = Application.builder().token('SEU_TOKEN_AQUI').build()

    # Adicionar os comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("entrada", entrada))
    application.add_handler(CommandHandler("saida", saida))
    application.add_handler(CommandHandler("saldo", saldo))
    application.add_handler(CommandHandler("relatorio", relatorio))
    application.add_handler(CommandHandler("limpar", limpar))
    application.add_handler(CommandHandler("ajuda", ajuda))

    # Agendar tarefa para rodar no 5º dia útil
    scheduler = BackgroundScheduler()
    scheduler.add_job(tarefa_agendada, 'cron', day_of_week='mon,tue,wed,thu,fri', hour=9, minute=0, id='tarefa_agendada')
    scheduler.start()

    application.run_polling()

if __name__ == '__main__':
    main()
