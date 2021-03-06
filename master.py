# Standard imports
import json
import time
import inspect

# Custom imports
import node
import messenger
import message
import taskunit
import job
import schedule


class Master(node.LocalNode):
    '''
    An instance of this class represents a master object who can assign work to
    its slaves after the job has been split up into work units.
    It then combines the results into the final expected result when it gets
    back the "intermediate results" from the slaves.
    '''
    def __init__(self, ip=None):
        '''
        FIXME: This param is unused for now. Maybe in the future we will need it
               in case we need to specify which interface to use.
        :param ip: Dot-delimited string representation of the ip of this node.
        '''
        super().__init__()

        self.pending_jobs = []
        self.completed_jobs = []
        self.slave_nodes = []
        self.scheduler = schedule.MinMakespan()
        self.messenger = messenger.Messenger()
        # A map of job_ids to Jobs.
        self.jobs = {}

    def process_job(self, new_job):
        '''TODO: MA: Implement this.
        This method takes a job as input and "processes" it in the sense
        that it generates TaskUnits from the Job and sends them off to the
        "right" Slaves to be processed.
        It then collects the results from our taskunits queue and combines
        them to get the final result.
        It then writes the results to a file and returns.
        '''
        for new_taskunit in new_job.splitter.split:
            print(new_taskunit)

    def get_node_address(self, node):
        '''
        Get the address for a remote node.
        '''
        return (node.address)

    def worker(self):
        '''
        This method keeps running for the life of the Slave. It asks for new
        messages from this Slave's messenger. It then appropriately handles
        the message. Some of the messages are TaskUnits return from the slaves
        after they have been processed.

        Other messages maybe status updates from the slaves or requests to send
        more work etc.
        '''
        while True:
            address, msg = self.messenger.receive(return_payload=False)
            if msg is None:
                time.sleep(2)
                continue

            msg_type = msg.msg_type
            if msg_type == message.Message.MSG_STATUS:
                status = int(msg.msg_payload.decode('utf-8'))
                # If the slave is sending a STATUS_UP, then store it in our
                # slave_nodes array.
                print("MASTER: STATE_UP received from %s:%d" % address)
                if status == node.Node.STATE_UP:
                    self.slave_nodes.append(node.RemoteNode(None, address))
                    self.scheduler.add_machine()
                    self.messenger.register_destination('slave1', address)
            elif msg_type == message.Message.MSG_JOB:
                print("MASTER: Got a new job.")
                object_dict = msg.msg_payload.decode('utf-8')
                j = job.Job.deserialize(object_dict)
                self.jobs[j.id] = j
                for tu in j.splitter.split(j.input_data, j.processor):
                    # The split method only fills in the data and the processor.
                    # So we need to manually fill the rest.
                    taskunit_id = taskunit.compute_taskunit_id(tu.data,
                                                               inspect.getsource(tu.processor))
                    tu.id = taskunit_id
                    tu.job_id = j.id

                    # Store this taskunit in the job's taskunit map.
                    j.taskunits[tu.id] = tu

                    # Now schedule this task unit.
                    next_slave = self.scheduler.schedule_job(tu)
                    slave_address = self.slave_nodes[next_slave].address

                    # Attributes to send to the slave.
                    attrs = ['id', 'job_id', 'data', 'processor._code',
                             'retries']
                    self.messenger.send_taskunit(tu, slave_address, attrs)
                j.pending_taskunits = len(j.taskunits)
            elif msg_type == message.Message.MSG_TASKUNIT_RESULT:
                # TODO: MA Handle failed tasks.
                print("MASTER: Got a taskunit result back.")
                tu = deserialized_msg
                job_id = tu.job_id
                j = self.jobs[job_id]
                taskunit_id = tu.id
                j.taskunits[taskunit_id].result = tu.result
                j.taskunits[taskunit_id].state = tu.state
                j.pending_taskunits -= 1
                if j.pending_taskunits == 0:
                    j.combiner.add_taskunits(j.taskunits.values())
                    j.combiner.combine()
