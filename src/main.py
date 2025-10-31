import logging
from src.database.base import create_tables, drop_tables
from src.database.seed import add_sample_data
from src.bot.core import bot
from src.bot import handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Запуск программы")

    drop_tables()
    create_tables()
    add_sample_data()
    bot.infinity_polling(skip_pending=True)
    
if __name__ == "__main__":
    main()