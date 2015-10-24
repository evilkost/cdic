# # coding: utf-8
# import datetime
# from datetime import timedelta
#
# from sqlalchemy.orm.exc import NoResultFound
# from sqlalchemy.orm.query import Query
# from sqlalchemy import or_, and_
#
# from ..models import JobState
#
#
# class TaskLogic(object):
#
#     def get_pending_tasks(self):
#         query = Task.query.filter(Task.retry_count < Task.max_retries)
#         tasks = query.filter(Task.state == JobState.NEW).all()
#
#         taken_tasks = query.filter(Task.state == JobState.TAKEN).all()
#
#         dt_now = datetime.datetime.utcnow()
#         expired_tasks = [
#             t for t in taken_tasks
#             if (dt_now - t.taken_on) < timedelta(seconds=t.max_execution_time)
#         ]
#
#         tasks.extend(expired_tasks)
#         return tasks
