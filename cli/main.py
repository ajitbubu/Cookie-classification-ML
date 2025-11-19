from config.logger_setup import setup_logger
from schedule_manager import run_scheduler
logger = setup_logger()

if __name__ == "__main__":
    print("Dynamic Cookie Scanning Service Started")
    run_scheduler()
