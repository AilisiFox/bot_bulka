import logging
from datetime import datetime, date
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import ScheduleManager, User, DatabaseManager
from config import Config

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.schedule_manager = ScheduleManager(db_manager)
        self.user_model = User(db_manager)
    
    async def handle_view_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict[str, Any]):
        try:
            schedule = self.schedule_manager.get_user_schedule(
                user['id'], 
                user['user_type']
            )
            
            if not schedule:
                await update.callback_query.edit_message_text(
                    "📅 **Ваше расписание пусто**\n\nУ вас пока нет запланированных уроков.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")
                    ]])
                )
                return

            message = "📅 **Ваше расписание:**\n\n"
            
            current_date = None
            for lesson in schedule:
                lesson_date = datetime.fromisoformat(lesson['lesson_date']).date()
                lesson_time = lesson['lesson_time']
                subject = lesson['subject'] or 'Урок'

                if current_date != lesson_date:
                    current_date = lesson_date
                    date_str = lesson_date.strftime("%d.%m.%Y (%A)")
                    message += f"\n📆 **{date_str}**\n"

                if user['user_type'] == 'teacher':
                    partner_name = f"{lesson['student_first_name']} {lesson['student_last_name']}"
                    icon = "👨‍🎓"
                else:
                    partner_name = f"{lesson['teacher_first_name']} {lesson['teacher_last_name']}"
                    icon = "👨‍🏫"
                
                message += f"🕐 {lesson_time} - {subject}\n"
                message += f"{icon} {partner_name}\n"
                message += f"⏱ {lesson['duration_minutes']} мин\n\n"

            keyboard = [
                [InlineKeyboardButton("📅 Сегодня", callback_data="schedule_today")],
                [InlineKeyboardButton("📅 Завтра", callback_data="schedule_tomorrow")],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
            ]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        except Exception as e:
            logger.error(f"Error viewing schedule: {e}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при загрузке расписания.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")
                ]])
            )
    
    async def handle_schedule_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     user: Dict[str, Any], filter_type: str):
        try:
            today = date.today()
            if filter_type == "today":
                target_date = today
                date_title = "Сегодня"
            else:
                from datetime import timedelta
                target_date = today + timedelta(days=1)
                date_title = "Завтра"
            
            schedule = self.schedule_manager.get_user_schedule(
                user['id'], 
                user['user_type'],
                target_date
            )
            
            if not schedule:
                message = f"📅 **{date_title}**\n\nУроков не запланировано."
            else:
                message = f"📅 **{date_title} ({target_date.strftime('%d.%m.%Y')})**\n\n"
                
                for lesson in schedule:
                    lesson_time = lesson['lesson_time']
                    subject = lesson['subject'] or 'Урок'
                    
                    if user['user_type'] == 'teacher':
                        partner_name = f"{lesson['student_first_name']} {lesson['student_last_name']}"
                        icon = "👨‍🎓"
                    else:
                        partner_name = f"{lesson['teacher_first_name']} {lesson['teacher_last_name']}"
                        icon = "👨‍🏫"
                    
                    message += f"🕐 {lesson_time} - {subject}\n"
                    message += f"{icon} {partner_name}\n"
                    message += f"⏱ {lesson['duration_minutes']} мин\n\n"
            
            keyboard = [
                [InlineKeyboardButton("📅 Все расписание", callback_data="view_schedule")],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
            ]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        except Exception as e:
            logger.error(f"Error filtering schedule: {e}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при загрузке расписания.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")
                ]])
            )
    
    async def handle_ai_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = (
            "🤖 **Генерация задач с помощью ИИ**\n\n"
            "Для создания образовательных задач с помощью искусственного интеллекта, "
            "перейдите по ссылке ниже:\n\n"
            f"🔗 {Config.AI_CHAT_URL}\n\n"
            "Там вы сможете:\n"
            "• Генерировать задания по любым предметам\n"
            "• Создавать тесты и контрольные работы\n"
            "• Получать идеи для уроков\n"
            "• Адаптировать материалы под разный уровень учеников"
        )
        
        keyboard = [
            [InlineKeyboardButton("🌐 Открыть ИИ чат", url=Config.AI_CHAT_URL)],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
        ]
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_reminder_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict[str, Any]):
        current_setting = "включены" if user['reminder_enabled'] else "выключены"
        
        message = (
            f"🔔 **Настройки напоминаний**\n\n"
            f"Текущий статус: {current_setting}\n\n"
            f"Напоминания отправляются за {Config.REMINDER_MINUTES_BEFORE} минут до начала урока.\n\n"
            "Выберите действие:"
        )
        
        keyboard = []
        if user['reminder_enabled']:
            keyboard.append([InlineKeyboardButton("🔕 Выключить напоминания", callback_data="toggle_reminders_off")])
        else:
            keyboard.append([InlineKeyboardButton("🔔 Включить напоминания", callback_data="toggle_reminders_on")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")])
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_toggle_reminders(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    user: Dict[str, Any], enable: bool):
        success = self.user_model.update_reminder_setting(user['telegram_id'], enable)
        
        if success:
            status = "включены" if enable else "выключены"
            message = f"✅ Напоминания успешно {status}!"
        else:
            message = "❌ Произошла ошибка при изменении настроек."
        
        keyboard = [
            [InlineKeyboardButton("🔔 Настройки напоминаний", callback_data="reminder_settings")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
        ]
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict[str, Any]):
        if user['user_type'] == 'teacher':
            message = (
                "ℹ️ **Помощь - Учитель**\n\n"
                "**Доступные функции:**\n\n"
                "📅 **Мое расписание** - просмотр ваших уроков\n"
                "🤖 **Генерация задач ИИ** - создание заданий с помощью ИИ\n"
                "🔔 **Настройки напоминаний** - управление уведомлениями\n\n"
                "**Голосовые сообщения:**\n"
                "Отправьте голосовое сообщение, и бот преобразует его в текст.\n\n"
                "**Напоминания:**\n"
                f"Автоматические уведомления за {Config.REMINDER_MINUTES_BEFORE} минут до урока.\n\n"
                "**Команды:**\n"
                "/start - главное меню\n"
                "/help - эта справка"
            )
        else:
            message = (
                "ℹ️ **Помощь - Ученик**\n\n"
                "**Доступные функции:**\n\n"
                "📅 **Мое расписание** - просмотр ваших уроков\n"
                "🔔 **Настройки напоминаний** - управление уведомлениями\n\n"
                "**Голосовые сообщения:**\n"
                "Отправьте голосовое сообщение, и бот преобразует его в текст.\n\n"
                "**Напоминания:**\n"
                f"Автоматические уведомления за {Config.REMINDER_MINUTES_BEFORE} минут до урока.\n\n"
                "**Команды:**\n"
                "/start - главное меню\n"
                "/help - эта справка"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
        ]
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )