import time
from rq import get_current_job
from app.app import create_app
from app.models import Task
from app.extensions import db
from flask import current_app
from cron import run
import sys
import traceback

app = create_app()
app.app_context()


def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue('app.tasks.' + name,
                                            *args, **kwargs)
    task = Task(id=rq_job.get_id(), name=name, description=description)
    db.session.add(task)
    return task


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())

        if progress >= 100:
            task.complete = True
        db.session.commit()


def full_sync():
    try:
        _set_task_progress(0)
        run()
    except Exception as e:
        _set_task_progress(100)
        print(f"there was an error: {e}")
    finally:
        _set_task_progress(100)
        print('Task Completed')
