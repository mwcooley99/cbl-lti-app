from app.app import create_app
from flask import current_app
from app.extensions import db
from app.models import Task

app = create_app()
app.app_context().push()


def launch_task(name, description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue('app.tasks.' + name,
                                            *args, **kwargs)
    task = Task(id=rq_job.get_id(), name=name, description=description)
    db.session.add(task)
    return task