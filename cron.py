from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import utc

from sqlalchemy import create_engine
from app.config import configuration
import os

from utilities.data_pull import (
    update_users,
    pull_outcome_results,
    insert_grades,
    update_courses,
    update_course_students,
    update_terms,
)

from utilities.db_functions import get_current_term

sched = BlockingScheduler(timezone=utc)


@sched.scheduled_job("cron", day_of_week="mon-fri", hour=8, minute=5)
def timed_job():
    print(f"job started at {datetime.now()}")
    config = configuration[os.getenv("PULL_CONFIG")]
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    update_terms(engine)
    print(f"terms updated at {datetime.now()}")
    # get current term
    current_term = get_current_term(engine)
    print(f"The current term is {current_term}")

    update_users(engine)
    print(f"users updated at {datetime.now()}")
    update_courses(current_term, engine)
    print(f"courses updated at {datetime.now()}")
    update_course_students(current_term, engine)
    print(f"course students updated at {datetime.now()}")
    pull_outcome_results(current_term, engine)
    print(f"outcome_results pulled at {datetime.now()}")
    insert_grades(engine, current_term)
    print(f"grades inserted at {datetime.now()}")
    engine.dispose()

if __name__ == "__main__":
    sched.start()
