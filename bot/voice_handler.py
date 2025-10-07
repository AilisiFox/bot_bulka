import os
import logging
import tempfile
from typing import Optional
import openai
from telegram import Update, File
from telegram.ext import ContextTypes
from config import Config

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.openai_client = None
        if Config.OPENAI_API_KEY != 'YOUR_OPENAI_API_KEY_HERE':
            openai.api_key = Config.OPENAI_API_KEY
            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

        os.makedirs(Config.AUDIO_TEMP_DIR, exist_ok=True)
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящих голосовых сообщений"""
        if not self.openai_client:
            await update.message.reply_text(
                "❌ Распознавание голоса недоступно. OpenAI API ключ не настроен."
            )
            return
        
        try:
            processing_msg = await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
            
            voice = update.message.voice
            if not voice:
                await processing_msg.edit_text("❌ Не удалось получить голосовое сообщение.")
                return

            if voice.file_size > Config.MAX_AUDIO_SIZE_MB * 1024 * 1024:
                await processing_msg.edit_text(
                    f"❌ Размер файла слишком большой. Максимум: {Config.MAX_AUDIO_SIZE_MB}MB"
                )
                return

            file: File = await context.bot.get_file(voice.file_id)

            with tempfile.NamedTemporaryFile(
                suffix='.ogg', 
                dir=Config.AUDIO_TEMP_DIR, 
                delete=False
            ) as temp_file:
                temp_path = temp_file.name
                await file.download_to_drive(temp_path)
            
            try:
                transcription = await self.transcribe_audio(temp_path)
                
                if transcription:
                    await processing_msg.edit_text(
                        f"📝 **Расшифровка голосового сообщения:**\n\n{transcription}"
                    )
                else:
                    await processing_msg.edit_text(
                        "❌ Не удалось распознать речь. Попробуйте говорить четче или отправить текстовое сообщение."
                    )
            
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке голосового сообщения. Попробуйте еще раз."
            )
    
    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Обрабатывает аудиофайл с помощью OpenAI Whisper"""
        try:
            with open(audio_path, 'rb') as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"
                )
                
                return response.text.strip()
        
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def handle_audio_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.openai_client:
            await update.message.reply_text(
                "❌ Распознавание аудио недоступно. OpenAI API ключ не настроен."
            )
            return
        
        try:
            processing_msg = await update.message.reply_text("🎵 Обрабатываю аудио сообщение...")
            
            audio = update.message.audio
            if not audio:
                await processing_msg.edit_text("❌ Не удалось получить аудио сообщение.")
                return

            if audio.file_size > Config.MAX_AUDIO_SIZE_MB * 1024 * 1024:
                await processing_msg.edit_text(
                    f"❌ Размер файла слишком большой. Максимум: {Config.MAX_AUDIO_SIZE_MB}MB"
                )
                return

            file: File = await context.bot.get_file(audio.file_id)

            file_extension = '.mp3'
            if audio.mime_type:
                if 'ogg' in audio.mime_type:
                    file_extension = '.ogg'
                elif 'wav' in audio.mime_type:
                    file_extension = '.wav'
                elif 'm4a' in audio.mime_type:
                    file_extension = '.m4a'
            
            with tempfile.NamedTemporaryFile(
                suffix=file_extension,
                dir=Config.AUDIO_TEMP_DIR,
                delete=False
            ) as temp_file:
                temp_path = temp_file.name
                await file.download_to_drive(temp_path)
            
            try:
                transcription = await self.transcribe_audio(temp_path)
                
                if transcription:
                    await processing_msg.edit_text(
                        f"📝 **Расшифровка аудио сообщения:**\n\n{transcription}"
                    )
                else:
                    await processing_msg.edit_text(
                        "❌ Не удалось распознать речь в аудио файле."
                    )
            
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        except Exception as e:
            logger.error(f"Error processing audio message: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке аудио сообщения."
            )