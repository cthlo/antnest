# Standard imports
import json
import hashlib

# Custom imports
import serialize
import taskunit


def compute_job_id(input_data, processor_code, split_code, combine_code):
    '''
    Compute the job_id.

    The job_id is the MD5 hash of the concatenation of the job's data,
    the processor_code, split method's code, combine_method's code.
    '''
    m = hashlib.md5()
    if isinstance(input_data, bytes):
        input_data_bytes = input_data
    else:
        input_data_bytes = bytes(input_data, 'UTF-8')

    if isinstance(processor_code, bytes):
        processor_code_bytes = processor_code
    else:
        processor_code_bytes = bytes(processor_code, 'UTF-8')

    if isinstance(split_code, bytes):
        split_code_bytes = split_code
    else:
        split_code_bytes = bytes(split_code, 'UTF-8')

    if isinstance(combine_code, bytes):
        combine_code_bytes = combine_code
    else:
        combine_code_bytes = bytes(combine_code, 'UTF-8')

    hashable = (input_data_bytes +
                processor_code_bytes +
                split_code_bytes +
                combine_code_bytes)
    m.update(hashable)

    return m.hexdigest()


class Job(serialize.Serializable):
    '''
    An instance of this class represents a job to be run on a distributed
    system cluster. The job defines a splitter, a combiner, the input to the
    job, the processor for the taskunits.
    '''
    def __init__(self,
                 id=None,
                 input_data=None,
                 processor=None,
                 splitter=None,
                 combiner=None):
        '''
        :param input_data: An elementary type.

        :param splitter: An instance of Splitter. If None provided, an
        instance of the default splitter is used.

        :param combiner: An instance of Combiner. If None provided, an
        instance of the default combiner is used.

        :param processor: A function which every taskunit needs to be able
        to processor some given data into the required result.
        '''
        super().__init__(recursive_serialize=True)
        self.noserialize += ['taskunits']
        self.id = id

        self.__class__.processor = processor

        self.input_data = input_data

        self.splitter = splitter if splitter else Splitter()
        self.combiner = combiner if combiner else Combiner()

        # Map of taskunit ids to TaskUnits.
        self.taskunits = {}


class Splitter(serialize.Serializable):
    '''
    An instance of this class represents a splitter used by a master to "split"
    a job into smaller task units to be assigned to the slaves.
    The users of the system can define their own splitters to be used by the
    master.
    '''
    def __init__(self):
        super().__init__()
        self.noserialize += ['set_split_method']

    def set_split_method(self, split_method):
        '''
        Set the method to be used to split a job into taskunits.

        :param split_method: The new method to be used instead of the default
        split method below.
        '''
        self.__class__.split = split_method

    def split(self, input_data, processor):
        '''
        This method generates taskunits given an input file and the number of
        slaves to generate the taskunits for. The input_data is split at
        newlines and one taskunit is created for each line.

        This method can be overwritten if the users of the system decides to
        use their own splitter.

        :param processor: The processor for each "split". Each split is
        basically a taskunit.
        '''
        input_lines = input_data.split('\n')
        for input_line in input_lines:
            t = taskunit.TaskUnit(data=input_line, processor=processor)
            yield t


class Combiner(serialize.Serializable):
    '''
    An instance of this class represents a combiner used by a master to
    combine the results from taskunits.

    The users of the system can define their own combiners to be used by the
    master.
    '''
    def __init__(self):
        super().__init__()
        self.noserialize += ['set_combine_method', 'add_taskunits', 'taskunits']
        self.taskunits = []

    def set_combine_method(self, combine_method):
        '''
        Set the method to be used to combine the results from taskunits.
        '''
        self.__class__.combine = combine_method

    def add_taskunits(self, tu):
        '''
        Add a taskunit to combine.

        When all the taskunits are available (determined by the master),
        the combine() method needs to called to actually combine the results.
        '''
        self.taskunits.extend(tu)

    def combine(self):
        '''
        This method takes as input a list of taskunits and combines their
        results into the final result.

        This method just uses the "sum" operator to combine all the results
        and then dumps the results as a JSON string to the file
        result_<date>.json

        In most situations, the system users would want to define their own
        combine method to combine the results.
        '''
        taskunits = self.taskunits
        results = [t.result for t in taskunits]
        combined_result = sum(results)  # Just sum the values.
        json_string = json.dumps(combined_result, indent=2)
        result_file = open('result_' + time.strftime('%Y-%m-%d_%H:%M:%S'), 'w')
        result_file.write(json_string)
        result_file.close()
