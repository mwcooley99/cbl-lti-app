import time
from rq import get_current_job
from app.models import Task
from app.extensions import db
from flask import current_app

def example(seconds):
    job = get_current_job()
    print('Starting task')
    for _i in range(seconds):
        job.meta["progress"] = 100.0 * _i / seconds
        job.save_meta()
        print(_i)
        time.sleep(1)
    job.meta["progress"] = 100
    job.save_meta()
    print('Task Completed')


def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue('app.tasks.' + name,
                                            *args, **kwargs)
    task = Task(id=rq_job.get_id(), name=name, description=description)
    db.session.add(task)
    return task