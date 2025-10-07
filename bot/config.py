import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY_HERE')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///telegram_bot.db')
    REMINDER_MINUTES_BEFORE = 15
    TIMEZONE = 'Europe/Moscow'
    AUDIO_TEMP_DIR = 'temp_audio'
    MAX_AUDIO_SIZE_MB = 20
    SUPPORTED_AUDIO_FORMATS = ['.ogg', '.mp3', '.wav', '.m4a']
    AI_CHAT_URL = "https://chat.openai.com"
    
    @classmethod
    def validate_config(cls):
        """Валидация конфига"""
        if cls.TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError("TELEGRAM_BOT_TOKEN must be set")
        
        if cls.OPENAI_API_KEY == 'YOUR_OPENAI_API_KEY_HERE':
            print("Warning: OPENAI_API_KEY not set, voice recognition will not work")
        
        return True