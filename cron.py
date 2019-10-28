from pytz import utc
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(timezone=utc)


@sched.scheduled_job('cron', day_of_week="mon", hour='23', minute=47)
def timed_job():
    # update_users()
    print("users updated")
    # preform_grade_pull()
    print("grades pulled")


from data_pull import update_users, preform_grade_pull

sched.start()
