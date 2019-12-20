from pytz import utc
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from data_pull import update_users, preform_grade_pull

sched = BlockingScheduler(timezone=utc)
print(datetime.now())


@sched.scheduled_job('cron', day_of_week="mon-fri", hour=6, minute=40)
def timed_job():
    print(f'job started at {datetime.now()}')
    update_users()
    print(f"users updated at {datetime.now()}")
    preform_grade_pull()
    print(f"grades pulled at {datetime.now()}")


sched.start()
