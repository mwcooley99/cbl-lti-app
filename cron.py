import schedule
import time

from data_pull import update_users, preform_grade_pull


def job():
    print("Hello World")


schedule.every().monday.at("3:47").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
