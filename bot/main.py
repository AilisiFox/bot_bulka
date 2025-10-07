import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

from config import Config
from models import DatabaseManager
from auth import AuthenticationManager
from voice_handler import VoiceHandler
from scheduler import ReminderScheduler
from handlers import BotHandlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        Config.validate_config()

        self.db_manager = DatabaseManager()
        self.auth_manager = AuthenticationManager(self.db_manager)
        self.voice_handler = VoiceHandler()
        self.bot_handlers = BotHandlers(self.db_manager)
        self.reminder_scheduler = None
        
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

        self.setup_handlers()
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("logout", self.auth_manager.logout))

        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))

        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_text_message
        ))
        self.application.add_handler(MessageHandler(
            filters.VOICE, 
            self.voice_handler.handle_voice_message
        ))
        self.application.add_handler(MessageHandler(
            filters.AUDIO, 
            self.voice_handler.handle_audio_message
        ))

        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context):
        await self.auth_manager.start_authentication(update, context)
    
    async def help_command(self, update: Update, context):
        user = await self.auth_manager.is_authenticated(update.effective_user.id)
        if user:
            await self.bot_handlers.handle_help(update, context, user)
        else:
            await update.message.reply_text(
                "ℹ️ **Помощь**\n\n"
                "Для начала работы с ботом введите команду /start и пройдите аутентификацию."
            )
    
    async def handle_text_message(self, update: Update, context):
        if context.user_data.get('awaiting_login'):
            await self.auth_manager.handle_login_input(update, context)
            return

        user = await self.auth_manager.is_authenticated(update.effective_user.id)
        if not user:
            await update.message.reply_text(
                "🔐 Для использования бота необходимо пройти аутентификацию.\n"
                "Введите команду /start"
            )
            return

        await update.message.reply_text(
            "💬 Сообщение получено!\n\n"
            "Для навигации по функциям бота используйте кнопки меню или команду /start"
        )
    
    async def handle_callback_query(self, update: Update, context):
        query = update.callback_query
        await query.answer()

        user = await self.auth_manager.is_authenticated(update.effective_user.id)

        if query.data == "cancel_auth":
            await self.auth_manager.handle_cancel_auth(update, context)
            return

        if not user:
            await query.edit_message_text(
                "🔐 Сессия истекла. Для продолжения работы введите /start"
            )
            return

        if query.data == "main_menu":
            await self.auth_manager.show_main_menu(update, context, user)
        
        elif query.data == "view_schedule":
            await self.bot_handlers.handle_view_schedule(update, context, user)
        
        elif query.data == "schedule_today":
            await self.bot_handlers.handle_schedule_filter(update, context, user, "today")
        
        elif query.data == "schedule_tomorrow":
            await self.bot_handlers.handle_schedule_filter(update, context, user, "tomorrow")
        
        elif query.data == "ai_tasks":
            if user['user_type'] == 'teacher':
                await self.bot_handlers.handle_ai_tasks(update, context)
            else:
                await query.edit_message_text("❌ Эта функция доступна только учителям.")
        
        elif query.data == "reminder_settings":
            await self.bot_handlers.handle_reminder_settings(update, context, user)
        
        elif query.data == "toggle_reminders_on":
            await self.bot_handlers.handle_toggle_reminders(update, context, user, True)
        
        elif query.data == "toggle_reminders_off":
            await self.bot_handlers.handle_toggle_reminders(update, context, user, False)
        
        elif query.data == "help":
            await self.bot_handlers.handle_help(update, context, user)
        
        else:
            await query.edit_message_text("❌ Неизвестная команда.")
    
    async def error_handler(self, update: Update, context):
        logger.error(f"Exception while handling an update: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке запроса. Попробуйте еще раз."
            )
    
    async def start_bot(self):
        logger.info("Starting Telegram bot...")

        self.reminder_scheduler = ReminderScheduler(self.application, self.db_manager)
        self.reminder_scheduler.start()

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot is running...")

        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
        finally:
            await self.stop_bot()
    
    async def stop_bot(self):
        if self.reminder_scheduler:
            self.reminder_scheduler.stop()
        
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        logger.info("Bot stopped.")

def main():
    try:
        bot = TelegramBot()
        asyncio.run(bot.start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()