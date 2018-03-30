import os
from .utf_groundtruth_parser import UtfGroundTruthParser


class RT09Parser:
    def __init__(self, config):
        self.elements = []
        self.data_in_base_dir = config["data"]["base_dir"]
        self.dataset_to_use = config["data"]["dataset_to_use"]
        self.converted_file_format = "wav"

    def _fetch_file_in_folder(self, endswith, folder=None):
        if folder is None:
            folder = self.data_in_base_dir
        f = None
        for path, dirs, files in os.walk(folder):
            counter = 0
            for filename in files:
                if filename.endswith(endswith):
                    counter += 1
                    if counter > 1:
                        raise Exception(
                            "Too many files ending with %s present! Maybe you are trying to run different tasks at once - do not do that!" % (
                                endswith))
                    f = os.path.join(path, filename)
        return f

    def _parse_uem(self):
        lines = [line.strip() for line in open(self._fetch_file_in_folder(endswith=".uem"), 'r').readlines() if
                 not line.strip().startswith(';')]
        for line in lines:
            entry = line.split(' ')
            if entry[0] == self.dataset_to_use:
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
        lines = [line.strip() for line in open(self._fetch_file_in_folder(endswith='audioList.txt'), 'r').readlines() if
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
                bashCommand = ['sph2pipe', '-p', '-f', self.converted_file_format, '-c', '1', filehandle,
                               convertedFilehandle]
                # bashCommand = ['sox', '-t', 'sph', filehandle, '-b', '16', '-t', 'wav', convertedFilehandle]
                process = os.subprocess.Popen(bashCommand, stdout=os.subprocess.PIPE)
                output, error = process.communicate()

                if error is not None:
                    raise Exception("An error occured during conversion (%s): %s" % (output, error))

    def parse(self):
        self._parse_uem()

        self._parse_audiolist()

        self._convert_files()

        self._parse_ground_truth()

        return self.elements
