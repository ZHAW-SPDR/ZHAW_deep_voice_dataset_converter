import os
import random
import argparse


class VoxCelebSpeakerListGenerator:
    def __init__(self, path, speaker_count):
        self.path = path
        self.speaker_count = speaker_count

    def create_speaker_list_file(self):
        speakers = self._get_speaker_names()

        print(speakers[0:100])
        random.shuffle(speakers)
        print(speakers[0:100])

        with open("speakers_voxceleb_%s.txt" % self.speaker_count, mode="w") as speaker_file:
            speaker_file.writelines(
                map(lambda speaker: "%s\n" % speaker, speakers[0:self.speaker_count])
            )

    def _get_speaker_names(self):
        return [name for name in os.listdir(self.path) if os.path.isdir(os.path.join(self.path, name))]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Creates a speaker list of the VoxCeleb dataset to just use a subset in the ZHAW_deep_voice, as training")

    parser.add_argument("path", metavar="p", help="Path to the VoxCeleb dataset")

    args = parser.parse_args()

    generator = VoxCelebSpeakerListGenerator(
        args.path,
        100)

    generator.create_speaker_list_file()
