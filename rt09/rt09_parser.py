import os
import subprocess
from .utf_groundtruth_parser import UtfGroundTruthParser


class RT09Parser:
    def __init__(self, evaluation_set, config):
        self.elements = []
        self.evaluation_set = evaluation_set
        self.task = config["data"]["task"]
        self.data_in_base_dir = config["data"]["base_dir"]
        self.converted_file_format = "wav"

    def _fetch_file_in_folder(self, endswith, contains="", folder=None):
        if folder is None:
            folder = self.data_in_base_dir
        f = None
        for path, dirs, files in os.walk(folder):
            counter = 0
            for filename in files:
                if filename.endswith(endswith) and filename.find(contains) != -1:
                    counter += 1
                    if counter > 1:
                        raise Exception(
                            "Too many files ending with %s and containing '%s' present! Maybe you are trying to run different tasks at once - do not do that!" % (
                                endswith, contains))
                    f = os.path.join(path, filename)
        return f

    def _parse_uem(self):
        lines = [line.strip() for line in open(self._fetch_file_in_folder(endswith=".uem", contains=self.task), 'r').readlines() if
                 not line.strip().startswith(';')]
        for line in lines:
            entry = line.split(' ')
            if entry[0] != self.evaluation_set:
                self.elements.append({
                    'id': entry[0],
                    'channel': entry[1],
                    'start': entry[2],
                    'end': entry[3]
                })

    @staticmethod
    def _get_dataset_folder(folder):
        trailing_paths = folder.split("/")[-2:]
        return os.path.join(trailing_paths[0], trailing_paths[1])

    def _parse_audiolist(self):
        lines = [line.strip() for line in open(self._fetch_file_in_folder(endswith='audioList.txt', contains=self.task), 'r').readlines() if
                 not line.strip().startswith(';')]
        for line in lines:
            entry = line.split(' ')
            identifier = entry[0]

            files = [os.path.join(self.data_in_base_dir, self._get_dataset_folder(e)) for e in entry[1:len(entry)]]
            for element in self.elements:
                if element['id'] == identifier:
                    element['files'] = files

    def _parse_ground_truth(self):
        parser = UtfGroundTruthParser()

        for element in self.elements:
            utf_file = os.path.join(self.data_in_base_dir, element["id"], "%s.%s" % (element["id"], "utf"))
            element["turns"] = parser.parse(utf_file)

    def _convert_files(self):
        for element in self.elements:
            for filehandle in element['files']:

                convertedFilehandle = filehandle.replace('sph', self.converted_file_format)
                if os.path.isfile(convertedFilehandle):
                    continue

                print('Converting File %s' % filehandle)

                bash_command = ['sox', '-t', 'sph', filehandle, '-r', '16000', '-c', '1', '-t',
                                self.converted_file_format, convertedFilehandle]

                process = subprocess.Popen(bash_command, stdout=subprocess.PIPE)
                output, error = process.communicate()

                if error is not None:
                    raise Exception("An error occured during conversion (%s): %s" % (output, error))

    def parse(self):
        self._parse_uem()

        self._parse_audiolist()

        self._convert_files()

        self._parse_ground_truth()

        return self.elements
