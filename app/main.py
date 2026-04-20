import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to sys.path to make app a package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.telegram_bot import TelegramBot

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credential.env')
load_dotenv(dotenv_path=env_path)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    bot = TelegramBot(token)
    bot.setup()
    bot.run()

if __name__ == '__main__':
    main()
