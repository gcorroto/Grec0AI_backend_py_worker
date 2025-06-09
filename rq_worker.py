from redis import Redis
from rq import Worker, Queue, Connection

listen = [
    'scripts_queue',
    'video_scripts_queue',
    'frames_scripts_queue',
    'metadata_scripts_queue',
    'frontend_queue'
]

redis_conn = Redis(host='127.0.0.1', port=6379, db=0)

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker([Queue(name) for name in listen])
        worker.work()
