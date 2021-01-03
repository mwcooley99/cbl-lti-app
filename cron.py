from datetime import datetime
import re

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
    query_current_outcome_results,
)

from utilities.db_functions import get_sync_terms

sched = BlockingScheduler(timezone=utc)


def run():
    print(f"job started at {datetime.now()}")
    config = configuration[os.getenv("PULL_CONFIG")]
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)

    update_terms(engine)
    print(f"terms updated at {datetime.now()}")

    # get the "sync" terms
    sync_terms = get_sync_terms(engine)
    print(f"The sync terms are {[term['id'] for term in sync_terms]}")

    update_users(engine)
    print(f"users updated at {datetime.now()}")

    for term in sync_terms:
        print(f"syncing term {term['id']}")
        
        update_courses(term, engine)
        print(f"courses updated at {datetime.now()}")

        update_course_students(term, engine)
        print(f"course students updated at {datetime.now()}")
        
        pull_outcome_results(term, engine)
        print(f"outcome_results pulled at {datetime.now()}")

        insert_grades(term, engine)
        print(f"grades inserted at {datetime.now()}")

    engine.dispose()


@sched.scheduled_job("cron", day_of_week="sun, mon, tues, wed, thu", hour=18, minute=5)
def timed_job():
    run()


if __name__ == "__main__":
    sched.start()
