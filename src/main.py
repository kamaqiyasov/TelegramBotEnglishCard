from src.database.base import create_tables
from src.bot.core import bot
from src.bot import handlers

def main():
    create_tables()
    bot.infinity_polling(skip_pending=True)
    
if __name__ == "__main__":
    main()