import json
import os
import asyncio
from prettytable import PrettyTable
from pystockfilter.tool.start_backtest import StartBacktest
from pystockfilter.data.stock_data_source import DataSourceModule as Data
from pystockfilter.strategy.rsi_strategy import RSIStrategy
from telegram import Bot
from telegram.constants import ParseMode

def load_environment_variables():
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    if not bot_token or not chat_id:
        raise ValueError("Please ensure both BOT_TOKEN and CHAT_ID are set as environment variables.")
    return bot_token, chat_id

async def generate_backtest_results(data):
    results = []
    for ticker, strategy_dict in data.items():
        rsi_params = strategy_dict['RSIStrategy']["parameter"]
        bt = StartBacktest([ticker], [RSIStrategy], [rsi_params], Data(source=Data.Y_FINANCE))
        results.extend(bt.run())
    return results

def save_results_to_file(results, filename):
    sorted_results = sorted(
        results, 
        key=lambda x: ({"BUY": 0, "SELL": 1, "HOLD": 2}.get(x.status.name, 3), -x.earnings)
    )
    with open(filename, 'w') as file:
        json.dump([{
            'symbol': result.symbol,
            'status': result.status.name,
            'sqn': result.sqn,
            'earnings': result.earnings
        } for result in sorted_results], file, indent=4)
    return sorted_results

def create_pretty_table(results):
    table = PrettyTable(['Symbol', 'Status', 'SQN', 'Earnings'])
    table.align['Symbol'] = 'l'
    table.align['Status'] = 'l'
    table.align['SQN'] = 'r'
    table.align['Earnings'] = 'r'
    
    for result in results:
        row = [result.symbol, result.status.name, f'{result.sqn:.2f}', f'{result.earnings:.2f}']
        table.add_row(row)
    return table

async def send_telegram_message(bot_token, chat_id, table):
    bot = Bot(token=bot_token)
    try:
        headline_html = "<b>📊 RSIStrategy Backtest Results 📊</b>\n\n"
        await bot.send_message(
            chat_id=chat_id,
            text=f'{headline_html}<pre>{table}</pre>',
            parse_mode=ParseMode.HTML
        )
        print("Messages sent successfully.")
    except Exception as e:
        print(f"Error: {e}")

async def send_backtest_table():
    """Generate a backtest results table and send it via Telegram."""
    with open("parameter.json", "r") as json_file:
        data = json.load(json_file)

    results = await generate_backtest_results(data)
    sorted_results = save_results_to_file(results, 'backtest_results.json')
    table = create_pretty_table(sorted_results)
    bot_token, chat_id = load_environment_variables()
    await send_telegram_message(bot_token, chat_id, table)

if __name__ == "__main__":
    asyncio.run(send_backtest_table())
