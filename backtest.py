import json
import os
import asyncio
from prettytable import PrettyTable
from pystockfilter.tool.start_backtest import StartBacktest
from pystockfilter.data.stock_data_source import DataSourceModule as Data
from pystockfilter.strategy.rsi_strategy import RSIStrategy
from pystockfilter.strategy.uo_strategy import UltimateStrategy
from telegram import Bot
from telegram.constants import ParseMode

MESSAGE_SIZE_LIMIT = 4096  # Telegram message size limit
CHUNK_SIZE = 50  # Adjust based on average row length to fit within limit

def load_environment_variables():
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    if not bot_token or not chat_id:
        raise ValueError("Please ensure both BOT_TOKEN and CHAT_ID are set as environment variables.")
    return bot_token, chat_id

async def generate_backtest_results(data, strategy_name):
    results = []
    for ticker, strategy_dict in data.items():
        if strategy_name in strategy_dict:
            params = strategy_dict[strategy_name]["parameter"]
            strategy_class = globals().get(strategy_name)
            bt = StartBacktest([ticker], [strategy_class], [params], Data(source=Data.Y_FINANCE))
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

def split_results_into_chunks(results, chunk_size):
    return [results[i:i + chunk_size] for i in range(0, len(results), chunk_size)]

async def send_telegram_message(bot_token, chat_id, table, strategy_name, part):
    bot = Bot(token=bot_token)
    try:
        headline_html = f"<b>📊 {strategy_name} Backtest Results - Part {part} 📊</b>\n\n"
        await bot.send_message(
            chat_id=chat_id,
            text=f'{headline_html}<pre>{table}</pre>',
            parse_mode=ParseMode.HTML
        )
        print(f"{strategy_name} Part {part} messages sent successfully.")
    except Exception as e:
        print(f"Error: {e}")

async def send_backtest_tables(strategy_names):
    """Generate backtest result tables for multiple strategies and send them via Telegram."""
    with open("parameter_v2.json", "r") as json_file:
        data = json.load(json_file)

    bot_token, chat_id = load_environment_variables()

    for strategy_name in strategy_names:
        results = await generate_backtest_results(data, strategy_name)
        sorted_results = save_results_to_file(results, f'backtest_results_{strategy_name}.json')
        result_chunks = split_results_into_chunks(sorted_results, CHUNK_SIZE)

        for i, chunk in enumerate(result_chunks, 1):
            table = create_pretty_table(chunk)
            await send_telegram_message(bot_token, chat_id, table, strategy_name, i)

if __name__ == "__main__":
    strategy_names =  os.getenv('STRATEGY_NAMES', "UltimateStrategy,RSIStrategy").split(",")
    asyncio.run(send_backtest_tables(strategy_names))
