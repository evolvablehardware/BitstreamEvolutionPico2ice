import itertools
from logging import Logger
from typing import List, Dict, Any
from icefarm.client.drivers import PulseCountClient
from icefarm.client.lib.pulsecount import PulseCountEvaluation
from Circuit.FileBasedCircuit import FileBasedCircuit
from Circuit import FitnessFunction

class RemoteCircuit(FileBasedCircuit):
    def __init__(self, client: "EvolutionClient", serials: List[str], index, filename, config, template, rand, logger, fitnessfunc: FitnessFunction):
        super().__init__(index, filename, config, template, rand, logger)
        self._client = client
        self._serials = serials
        self._fitnessfunc = fitnessfunc
        self._extra_data = {}
        self._fitnessfunc.attach(filename, None, config, self._extra_data)

    def collect_data_once(self):
        # data is appended during fitness calculation
        # this allows all the circuits to be sent at once
        return

    def _get_measurement(self): ...
        # makes abc happy

    def upload(self):
        self._extra_data = {}
        self.clear_data()
        self._compile()
        self._client.evaluate(self._serials, self)

    # called by randomize until
    def evaluate_once(self):
        self.upload()

    def _calculate_fitness(self):
        if not self._data:
            results = self._client.get_result(self)
            # TODO add an additional log file that maps serials to pulses
            if self._serials:
                self._data = [int(results[serial]) for serial in self._serials]
            else:
                self._data = [int(result) for result in results.values()]

            self._extra_data["pulses"] = self._data

        return self._fitnessfunc.calculate_fitness(self._data)

    def get_extra_data(self, key):
        return self._extra_data[key]

    def _get_all_live_reported_value(self):
        return self._extra_data["pulses"]

class EvolutionClient:
    """
    Wrapper around icefarm PulseCountClient to allow RemoteCircuit api to be the same as other circuits.
    """
    def __init__(self, client: PulseCountClient, logger: Logger):
        self._client = client
        self._command_queue = []
        self._result_map = {}
        self._logger = logger

    def evaluate(self, serials: List[str] | None, circuit: FileBasedCircuit):
        """
        Queues circuit to be evaluated on picos with identification of serials.
        If no serial is given, one is assigned based on the optimal evaluation speed.
        """
        self._result_map = {}
        self._command_queue.append((serials, circuit._bitstream_filepath))

    def get_result(self, circuit: FileBasedCircuit) -> Dict[str, Any]:
        """
        Returns map of serial to results after they arrive from the iCEFARM system.
        The first time this is called, evaluations are sent to iCEFARM.
        """
        if not self._result_map:
            assigned_evaluations = [PulseCountEvaluation(serials, filepath) for serials, filepath in self._command_queue if serials]
            unassigned_evaluations = (filepath for serials, filepath in self._command_queue if not serials)

            # TODO
            # Divides evaluations that don't care where they end up
            # among devices. This is not optimal if using a mix of assigned and
            # unassigned evaluations, but doing so is complicated and I
            # am going to add to icefarm instead of here
            batches = itertools.batched(unassigned_evaluations, len(self._client.getSerials()))

            for batch in batches:
                for serial, fpath in zip(self._client.getSerials(), batch):
                    assigned_evaluations.append(PulseCountEvaluation([serial], fpath))

            self._logger.info("Sending circuits for remote evaluation...")

            for serial, evaluation, result in self._client.evaluateEvaluations(assigned_evaluations):
                fpath = evaluation.filepath
                if fpath not in self._result_map:
                    self._result_map[fpath] = {}

                self._result_map[fpath][serial] = float(result)
                self._logger.debug(f"Received value for file {fpath}: {result}")

            self._logger.info("Remote evaluation complete.")
            self._command_queue = []

        return self._result_map[circuit._bitstream_filepath]
