from src.database.base import create_tables, drop_tables
from src.database.seed import add_sample_data
from src.bot.core import bot
from src.bot import handlers

if __name__ == "__main__":
    drop_tables()
    create_tables()
    add_sample_data()
    print("bot running")
    bot.infinity_polling(skip_pending=True)