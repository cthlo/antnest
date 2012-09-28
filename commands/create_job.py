# Standard imports
import argparse
import socket
import importlib
import time

# Custom imports
import messenger
from job import Job, Splitter, Combiner

def enqueue_job(jobfile):
    # Bind to some other port. Not to the main 33310.
    m = messenger.Messenger(port=33311)
    my_hostname = socket.gethostname()
    m.register_destination(socket.gethostname(),
                           ('0.0.0.0', 33310))
    # This file contains at most 3 methods: split, combine, processor and 2
    # variables: input_data. input_file
    jobcode = importlib.import_module('jobs.%s' % jobfile)
    try:
        combiner = Combiner()
        combiner.combine = jobcode.combine
    except:
        combiner = None

    try:
        splitter = Splitter()
        splitter.split = jobcode.split
    except:
        splitter = None

    job = Job(processor=jobcode.processor,
              input_file=jobcode.input_file,
              splitter=splitter,
              combiner=combiner)
    try:
        job.input_data = jobcode.input_data
    except:
        pass

    m.send_job(job, my_hostname)
    while len(m.outbound_queue[my_hostname]):
        print("Job still not sent out...sleeping.")
        time.sleep(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='As a master node, enqueue a '
                                                 'new job to be processed by '
                                                 'this system.')
    parser.add_argument('--jobfile',
                        type=str,
                        help='the path to the file describing the job')

    args = parser.parse_args()
    enqueue_job(args.jobfile)