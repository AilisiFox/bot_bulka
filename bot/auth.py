import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import User, DatabaseManager

logger = logging.getLogger(__name__)

class AuthenticationManager:
    def __init__(self, db_manager: DatabaseManager):
        self.user_model = User(db_manager)
        self.pending_auth = {}
    
    async def is_authenticated(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        return self.user_model.get_user_by_telegram_id(telegram_id)
    
    async def start_authentication(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id

        user = await self.is_authenticated(telegram_id)
        if user:
            await self.show_main_menu(update, context, user)
            return

        await update.message.reply_text(
            "👋 Привет! Я бот-помощник для учителей и учеников.\n\n"
            "Для начала работы введите ваш логин:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_auth")
            ]])
        )

        context.user_data['awaiting_login'] = True
    
    async def handle_login_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.user_data.get('awaiting_login'):
            return
        
        login = update.message.text.strip()
        telegram_id = update.effective_user.id
        user_info = self.user_model.authenticate_user(login)
        
        if user_info:
            if user_info['telegram_id'] and user_info['telegram_id'] != telegram_id:
                await update.message.reply_text(
                    "❌ Этот логин уже привязан к другому Telegram аккаунту."
                )
                context.user_data['awaiting_login'] = False
                return

            if not user_info['telegram_id']:
                success = self.user_model.bind_telegram_id(
                    login, telegram_id, user_info['user_type']
                )
                if not success:
                    await update.message.reply_text(
                        "❌ Ошибка при привязке аккаунта. Попробуйте еще раз."
                    )
                    return

            context.user_data['awaiting_login'] = False

            user = await self.is_authenticated(telegram_id)
            
            await update.message.reply_text(
                f"✅ Добро пожаловать, {user['first_name']} {user['last_name']}!\n"
                f"Вы вошли как: {'Учитель' if user['user_type'] == 'teacher' else 'Ученик'}"
            )
            
            await self.show_main_menu(update, context, user)
            
        else:
            await update.message.reply_text(
                "❌ Логин не найден. Проверьте правильность ввода и попробуйте еще раз.\n\n"
                "Введите ваш логин:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отмена", callback_data="cancel_auth")
                ]])
            )
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict[str, Any]):
        if user['user_type'] == 'teacher':
            keyboard = [
                [InlineKeyboardButton("📅 Мое расписание", callback_data="view_schedule")],
                [InlineKeyboardButton("🤖 Генерация задач ИИ", callback_data="ai_tasks")],
                [InlineKeyboardButton("🔔 Настройки напоминаний", callback_data="reminder_settings")],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
            ]
            text = f"🎓 Добро пожаловать, {user['first_name']} {user['last_name']}!\n\nВыберите действие:"
        else:
            keyboard = [
                [InlineKeyboardButton("📅 Мое расписание", callback_data="view_schedule")],
                [InlineKeyboardButton("🔔 Настройки напоминаний", callback_data="reminder_settings")],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
            ]
            text = f"📚 Добро пожаловать, {user['first_name']} {user['last_name']}!\n\nВыберите действие:"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def handle_cancel_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['awaiting_login'] = False
        await update.callback_query.edit_message_text(
            "❌ Аутентификация отменена.\n\nДля начала работы нажмите /start"
        )
    
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id  # noqa: F841

        context.user_data.clear()
        
        await update.message.reply_text(
            "👋 Вы вышли из системы.\n\nДля повторного входа нажмите /start"
        )