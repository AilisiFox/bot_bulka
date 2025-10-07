import logging
from datetime import datetime
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
from telegram.ext import Application
from models import ScheduleManager, DatabaseManager
from config import Config

logger = logging.getLogger(__name__)

class ReminderScheduler:
    def __init__(self, bot_application: Application, db_manager: DatabaseManager):
        self.bot_application = bot_application
        self.schedule_manager = ScheduleManager(db_manager)
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(Config.TIMEZONE))
        self.is_running = False
    
    def start(self):
        """Запуск планировщика напоминаний"""
        if not self.is_running:
            self.scheduler.add_job(
                self.check_reminders,
                CronTrigger(second=0),
                id='reminder_check',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("Reminder scheduler started")
    
    def stop(self):
        """Остановка планировщика напоминаний"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Reminder scheduler stopped")
    
    async def check_reminders(self):
        try:
            upcoming_lessons = self.schedule_manager.get_upcoming_lessons(Config.REMINDER_MINUTES_BEFORE)
            
            for lesson in upcoming_lessons:
                await self.send_reminder(lesson)
        
        except Exception as e:
            logger.error(f"Error checking reminders: {e}")
    
    async def send_reminder(self, lesson: Dict[str, Any]):
        """Проверка наличие уроков, требующих напоминаний"""
        try:
            lesson_time = lesson['lesson_time']
            subject = lesson['subject'] or 'Урок'

            if lesson['teacher_reminder_enabled'] and lesson['teacher_telegram_id']:
                teacher_message = (
                    f"🔔 **Напоминание об уроке**\n\n"
                    f"📚 Предмет: {subject}\n"
                    f"🕐 Время: {lesson_time}\n"
                    f"👨‍🎓 Ученик: {lesson['student_first_name']} {lesson['student_last_name']}\n\n"
                    f"Урок начнется через {Config.REMINDER_MINUTES_BEFORE} минут!"
                )
                
                await self.bot_application.bot.send_message(
                    chat_id=lesson['teacher_telegram_id'],
                    text=teacher_message
                )
                logger.info(f"Reminder sent to teacher {lesson['teacher_telegram_id']} for lesson {lesson['id']}")
            
            if lesson['student_reminder_enabled'] and lesson['student_telegram_id']:
                student_message = (
                    f"🔔 **Напоминание об уроке**\n\n"
                    f"📚 Предмет: {subject}\n"
                    f"🕐 Время: {lesson_time}\n"
                    f"👨‍🏫 Учитель: {lesson['teacher_first_name']} {lesson['teacher_last_name']}\n\n"
                    f"Урок начнется через {Config.REMINDER_MINUTES_BEFORE} минут!"
                )
                
                await self.bot_application.bot.send_message(
                    chat_id=lesson['student_telegram_id'],
                    text=student_message
                )
                logger.info(f"Reminder sent to student {lesson['student_telegram_id']} for lesson {lesson['id']}")
        
        except Exception as e:
            logger.error(f"Error sending reminder for lesson {lesson['id']}: {e}")
    
    def schedule_custom_reminder(self, telegram_id: int, message: str, reminder_time: datetime):
        """Настройка индивидуального напоминания"""
        try:
            job_id = f"custom_reminder_{telegram_id}_{reminder_time.timestamp()}"
            
            self.scheduler.add_job(
                self.send_custom_reminder,
                DateTrigger(run_date=reminder_time),
                args=[telegram_id, message],
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"Custom reminder scheduled for {telegram_id} at {reminder_time}")
            return job_id
        
        except Exception as e:
            logger.error(f"Error scheduling custom reminder: {e}")
            return None
    
    async def send_custom_reminder(self, telegram_id: int, message: str):
        """Отправка напоминаний"""
        try:
            await self.bot_application.bot.send_message(
                chat_id=telegram_id,
                text=f"🔔 **Напоминание**\n\n{message}"
            )
            logger.info(f"Custom reminder sent to {telegram_id}")
        
        except Exception as e:
            logger.error(f"Error sending custom reminder to {telegram_id}: {e}")
    
    def cancel_reminder(self, job_id: str) -> bool:
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Reminder {job_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling reminder {job_id}: {e}")
            return False
    
    def get_scheduled_jobs(self) -> List[str]:
        return [job.id for job in self.scheduler.get_jobs()]