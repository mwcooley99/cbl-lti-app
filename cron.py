from pytz import utc
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from data_pull import update_users, pull_outcome_results, insert_grades, update_courses

sched = BlockingScheduler(timezone=utc)
print(datetime.now())


@sched.scheduled_job('cron', day_of_week="mon-fri", hour=8, minute=5)
def timed_job():
    current_term = 11
    print(f'job started at {datetime.now()}')
    update_users()
    print(f"users updated at {datetime.now()}")
    update_courses(current_term)
    print(f"users updated at {datetime.now()}")
    pull_outcome_results(current_term)
    print(f"outcome_results pulled at {datetime.now()}")
    insert_grades(current_term)
    print(f"grades inserted at {datetime.now()}")


sched.start()
