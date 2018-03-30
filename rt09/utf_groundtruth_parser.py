from collections import namedtuple
import xml.etree.ElementTree as ET
import re

Turn = namedtuple("turn", ["startTime", "endTime", "speaker", "spkrType", "channel", "dialect"])


class UtfGroundTruthParser:

    @staticmethod
    def parse(filename):
        cleaned_utf = UtfGroundTruthParser._convert_to_valid_xml(filename)
        doc = ET.fromstring(cleaned_utf)
        conversation_root = doc.find("conversation_trans")
        turns = []

        for turn in conversation_root.iter("turn"):
            turns.append(Turn(**turn.attrib))

        return turns

    @staticmethod
    def _replacer(matchobj):
        if matchobj.group(5) == ">":
            return "<%s/>" % matchobj.group(1)

        return matchobj.group(5)

    @staticmethod
    def _convert_to_valid_xml(filename):
        with open(filename, mode="r") as utfFile:
            data = utfFile.read()
            cleaned_data = re.sub(r'<((contraction e_form="(\w|\[|\]|=>|\')*")|(fragment)|(e_unclear)|(b_unclear))(>)',
                                  UtfGroundTruthParser._replacer, data)
            return cleaned_data


if __name__ == '__main__':
    parser = UtfGroundTruthParser()
    parser.parse("/home/amin/studium_zhaw/Bachelor_Thesis/data/rt09/EDI_20071128-1000.utf")
