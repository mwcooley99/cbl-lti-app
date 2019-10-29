from pytz import utc
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(timezone=utc)


@sched.scheduled_job('cron', day_of_week="tue", hour='22', minute=00)
def timed_job():
    update_users()
    print(f"users updated at {datetime.now()}")
    preform_grade_pull()
    print(f"grades pulled at {datetime.now()}")


from data_pull import update_users, preform_grade_pull

sched.start()
