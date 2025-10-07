from datetime import date, time, timedelta
import logging
from models import DatabaseManager, Teacher, Student, Schedule, UserSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestDataPopulator:
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager(db_path)
    
    def populate_data(self):
        try:
            with self.db_manager.get_session() as session:
                logger.info("Clearing existing test data...")
                session.query(Schedule).delete()
                session.query(UserSession).delete()
                session.query(Teacher).delete()
                session.query(Student).delete()

                logger.info("Inserting test teachers...")
                teachers_data = [
                    Teacher(first_name="Анна", last_name="Петрова", login="teacher_anna", reminder_enabled=True),
                    Teacher(first_name="Михаил", last_name="Сидоров", login="teacher_mikhail", reminder_enabled=True),
                    Teacher(first_name="Елена", last_name="Козлова", login="teacher_elena", reminder_enabled=False),
                    Teacher(first_name="Дмитрий", last_name="Волков", login="teacher_dmitry", reminder_enabled=True),
                    Teacher(first_name="Ольга", last_name="Морозова", login="teacher_olga", reminder_enabled=True)
                ]
                
                for teacher in teachers_data:
                    session.add(teacher)

                logger.info("Inserting test students...")
                students_data = [
                    Student(first_name="Иван", last_name="Иванов", login="student_ivan", reminder_enabled=True),
                    Student(first_name="Мария", last_name="Смирнова", login="student_maria", reminder_enabled=True),
                    Student(first_name="Петр", last_name="Кузнецов", login="student_petr", reminder_enabled=False),
                    Student(first_name="Анастасия", last_name="Попова", login="student_anastasia", reminder_enabled=True),
                    Student(first_name="Алексей", last_name="Соколов", login="student_alexey", reminder_enabled=True),
                    Student(first_name="София", last_name="Лебедева", login="student_sofia", reminder_enabled=True),
                    Student(first_name="Максим", last_name="Новиков", login="student_maxim", reminder_enabled=False),
                    Student(first_name="Екатерина", last_name="Федорова", login="student_ekaterina", reminder_enabled=True)
                ]
                
                for student in students_data:
                    session.add(student)

                session.commit()

                teachers = session.query(Teacher).all()
                students = session.query(Student).all()

                logger.info("Inserting test schedule...")
                
                subjects = [
                    "Математика", "Русский язык", "Английский язык", 
                    "Физика", "Химия", "История", "География", "Биология"
                ]

                today = date.today()
                
                for day_offset in range(7):
                    current_date = today + timedelta(days=day_offset)

                    if current_date.weekday() >= 5:
                        continue

                    lessons_per_day = 4 if day_offset < 3 else 3
                    
                    for lesson_num in range(lessons_per_day):
                        lesson_times = [
                            time(9, 0), time(10, 30), time(12, 0), 
                            time(13, 30), time(15, 0)
                        ]
                        
                        if lesson_num < len(lesson_times):
                            lesson_time = lesson_times[lesson_num]

                            teacher = teachers[lesson_num % len(teachers)]
                            student = students[(lesson_num + day_offset) % len(students)]
                            subject = subjects[lesson_num % len(subjects)]
                            
                            schedule_entry = Schedule(
                                teacher_id=teacher.id,
                                student_id=student.id,
                                lesson_date=current_date,
                                lesson_time=lesson_time,
                                subject=subject,
                                duration_minutes=60,
                                status='scheduled'
                            )
                            session.add(schedule_entry)

                logger.info("Adding lessons for today...")
                today_lessons = [
                    Schedule(
                        teacher_id=teachers[0].id,
                        student_id=students[0].id,
                        lesson_date=today,
                        lesson_time=time(14, 30),
                        subject="Математика",
                        duration_minutes=60,
                        status='scheduled'
                    ),
                    Schedule(
                        teacher_id=teachers[1].id,
                        student_id=students[1].id,
                        lesson_date=today,
                        lesson_time=time(16, 0),
                        subject="Английский язык",
                        duration_minutes=60,
                        status='scheduled'
                    ),
                    Schedule(
                        teacher_id=teachers[2].id,
                        student_id=students[2].id,
                        lesson_date=today,
                        lesson_time=time(17, 30),
                        subject="Физика",
                        duration_minutes=60,
                        status='scheduled'
                    ),
                ]
                
                for lesson in today_lessons:
                    session.add(lesson)

                session.commit()

                teachers_count = session.query(Teacher).count()
                students_count = session.query(Student).count()
                schedule_count = session.query(Schedule).count()
                
                logger.info("Test data populated successfully!")
                logger.info(f"Teachers: {teachers_count}")
                logger.info(f"Students: {students_count}")
                logger.info(f"Schedule entries: {schedule_count}")

                print("\n" + "="*50)
                print("TEST LOGIN CREDENTIALS")
                print("="*50)
                
                print("\nTEACHERS:")
                for teacher in teachers:
                    print(f"  Login: {teacher.login} | Name: {teacher.first_name} {teacher.last_name}")
                
                print("\nSTUDENTS:")
                for student in students:
                    print(f"  Login: {student.login} | Name: {student.first_name} {student.last_name}")
                
                print("\n" + "="*50)
                print("Use these logins to test the bot authentication")
                print("="*50)
            
        except Exception as e:
            logger.error(f"Error populating test data: {e}")
            raise

def main():
    print("Telegram Bot - Test Data Population (SQLAlchemy)")
    print("This script will create test data for the bot database.")
    
    confirm = input("\nDo you want to proceed? This will clear existing data. (y/N): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    populator = TestDataPopulator()
    populator.populate_data()
    
    print("\nTest data population completed!")
    print("You can now test the bot with the provided login credentials.")

if __name__ == "__main__":
    main()