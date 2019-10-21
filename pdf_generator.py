from models import *

# Query the most recent record
current_record = Record.query.order_by(Record.id.desc()).first()

# Query all grades from that record
grades = Grade.query.filter_by(record_id=current_record.id)
# Get list of all user_ids - list of tuples
users = Grade.query.with_entities(Grade.user_id).filter_by(
    record_id=current_record.id).distinct().all()
# Loop through the user_ids - making a pdf for each

# Email?
