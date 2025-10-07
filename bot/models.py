from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Date, Time, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func
from datetime import date, time
from typing import Optional, List, Dict, Any
import logging
from contextlib import contextmanager
from config import Config
from sqlalchemy import and_, text

logger = logging.getLogger(__name__)

Base = declarative_base()

class Teacher(Base):
    __tablename__ = 'teachers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    login = Column(String(50), unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    reminder_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    schedule_as_teacher = relationship("Schedule", foreign_keys="[Schedule.teacher_id]", back_populates="teacher")
    
    def __repr__(self):
        return f"<Teacher(id={self.id}, name='{self.first_name} {self.last_name}', login='{self.login}')>"

class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    login = Column(String(50), unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    reminder_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    schedule_as_student = relationship("Schedule", foreign_keys="[Schedule.student_id]", back_populates="student")
    
    def __repr__(self):
        return f"<Student(id={self.id}, name='{self.first_name} {self.last_name}', login='{self.login}')>"

class Schedule(Base):
    __tablename__ = 'schedule'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    lesson_date = Column(Date, nullable=False)
    lesson_time = Column(Time, nullable=False)
    subject = Column(String(100), nullable=True)
    duration_minutes = Column(Integer, default=60)
    status = Column(String(20), default='scheduled')
    created_at = Column(DateTime, default=func.now())

    teacher = relationship("Teacher", foreign_keys=[teacher_id], back_populates="schedule_as_teacher")
    student = relationship("Student", foreign_keys=[student_id], back_populates="schedule_as_student")
    
    def __repr__(self):
        return f"<Schedule(id={self.id}, date={self.lesson_date}, time={self.lesson_time}, subject='{self.subject}')>"

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    user_type = Column(String(10), nullable=False)
    user_id = Column(Integer, nullable=False)
    is_authenticated = Column(Boolean, default=False)
    last_activity = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<UserSession(telegram_id={self.telegram_id}, user_type='{self.user_type}', authenticated={self.is_authenticated})>"

class DatabaseManager:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_database()
    
    def init_database(self):
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Менеджер контекста для сеансов базы данных"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        return self.SessionLocal()

class User:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def authenticate_user(self, login: str) -> Optional[Dict[str, Any]]:
        """
        Аутентификация пользователя путем входа
        в систему и возврат информации о пользователе
        """
        with self.db.get_session() as session:
            teacher = session.query(Teacher).filter(Teacher.login == login).first()
            if teacher:
                return {
                    'id': teacher.id,
                    'first_name': teacher.first_name,
                    'last_name': teacher.last_name,
                    'login': teacher.login,
                    'telegram_id': teacher.telegram_id,
                    'user_type': 'teacher'
                }

            student = session.query(Student).filter(Student.login == login).first()
            if student:
                return {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'login': student.login,
                    'telegram_id': student.telegram_id,
                    'user_type': 'student'
                }
            
            return None
    
    def bind_telegram_id(self, login: str, telegram_id: int, user_type: str) -> bool:
        """
        Привязка идентификатор Telegram к
        учетной записи пользователя
        """
        with self.db.get_session() as session:
            if user_type == 'teacher':
                user = session.query(Teacher).filter(Teacher.login == login).first()
            else:
                user = session.query(Student).filter(Student.login == login).first()
            
            if user:
                user.telegram_id = telegram_id

                user_session = session.query(UserSession).filter(
                    UserSession.telegram_id == telegram_id
                ).first()
                
                if user_session:
                    user_session.user_type = user_type
                    user_session.user_id = user.id
                    user_session.is_authenticated = True
                    user_session.last_activity = func.now()
                else:
                    user_session = UserSession(
                        telegram_id=telegram_id,
                        user_type=user_type,
                        user_id=user.id,
                        is_authenticated=True
                    )
                    session.add(user_session)
                
                return True
            return False
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе по идентификатору Telegram"""
        with self.db.get_session() as session:
            user_session = session.query(UserSession).filter(
                UserSession.telegram_id == telegram_id,
                UserSession.is_authenticated
            ).first()
            
            if not user_session:
                return None
            
            if user_session.user_type == 'teacher':
                user = session.query(Teacher).filter(Teacher.id == user_session.user_id).first()
            else:
                user = session.query(Student).filter(Student.id == user_session.user_id).first()
            
            if user:
                return {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'login': user.login,
                    'telegram_id': user.telegram_id,
                    'reminder_enabled': user.reminder_enabled,
                    'user_type': user_session.user_type
                }
            
            return None
    
    def update_reminder_setting(self, telegram_id: int, enabled: bool) -> bool:
        user_info = self.get_user_by_telegram_id(telegram_id)
        if not user_info:
            return False
        
        with self.db.get_session() as session:
            if user_info['user_type'] == 'teacher':
                user = session.query(Teacher).filter(Teacher.telegram_id == telegram_id).first()
            else:
                user = session.query(Student).filter(Student.telegram_id == telegram_id).first()
            
            if user:
                user.reminder_enabled = enabled
                return True
            return False

class ScheduleManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_user_schedule(self, user_id: int, user_type: str, date_filter: Optional[date] = None) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            query = session.query(Schedule)
            
            if user_type == 'teacher':
                query = query.filter(Schedule.teacher_id == user_id)
                query = query.join(Student, Schedule.student_id == Student.id)
            else:
                query = query.filter(Schedule.student_id == user_id)
                query = query.join(Teacher, Schedule.teacher_id == Teacher.id)
            
            if date_filter:
                query = query.filter(Schedule.lesson_date == date_filter)
            
            query = query.order_by(Schedule.lesson_date, Schedule.lesson_time)
            
            results = []
            for schedule in query.all():
                result = {
                    'id': schedule.id,
                    'lesson_date': schedule.lesson_date.isoformat(),
                    'lesson_time': schedule.lesson_time.isoformat(),
                    'subject': schedule.subject,
                    'duration_minutes': schedule.duration_minutes,
                    'status': schedule.status
                }
                
                if user_type == 'teacher':
                    result.update({
                        'student_first_name': schedule.student.first_name,
                        'student_last_name': schedule.student.last_name
                    })
                else:
                    result.update({
                        'teacher_first_name': schedule.teacher.first_name,
                        'teacher_last_name': schedule.teacher.last_name
                    })
                
                results.append(result)
            
            return results
    
    def get_upcoming_lessons(self, reminder_minutes: int = 15) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:

            query = session.query(Schedule).join(Teacher).join(Student).filter(
                and_(
                    Schedule.lesson_date == func.date('now'),
                    Schedule.status == 'scheduled',
                    text(f"TIME(schedule.lesson_time, '-{reminder_minutes} minutes') <= TIME('now')"),
                    text("TIME(schedule.lesson_time) > TIME('now')")
                )
            )
            
            results = []
            for schedule in query.all():
                results.append({
                    'id': schedule.id,
                    'lesson_date': schedule.lesson_date.isoformat(),
                    'lesson_time': schedule.lesson_time.isoformat(),
                    'subject': schedule.subject,
                    'teacher_first_name': schedule.teacher.first_name,
                    'teacher_last_name': schedule.teacher.last_name,
                    'teacher_telegram_id': schedule.teacher.telegram_id,
                    'teacher_reminder_enabled': schedule.teacher.reminder_enabled,
                    'student_first_name': schedule.student.first_name,
                    'student_last_name': schedule.student.last_name,
                    'student_telegram_id': schedule.student.telegram_id,
                    'student_reminder_enabled': schedule.student.reminder_enabled
                })
            
            return results
    
    def add_lesson(self, teacher_id: int, student_id: int, lesson_date: date, 
                   lesson_time: time, subject: str, duration: int = 60) -> bool:
        """Добаление нового урока в расписание"""
        with self.db.get_session() as session:
            lesson = Schedule(
                teacher_id=teacher_id,
                student_id=student_id,
                lesson_date=lesson_date,
                lesson_time=lesson_time,
                subject=subject,
                duration_minutes=duration
            )
            session.add(lesson)
            return True