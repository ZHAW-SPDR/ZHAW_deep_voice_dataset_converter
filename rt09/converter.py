import os
import random
import shutil
from collections import namedtuple, defaultdict
from .rt09_parser import RT09Parser
from pydub import AudioSegment

SpeakerSegment = namedtuple("SpeakerSegment", ["filename", "start", "end"])
Speaker = namedtuple("Speaker", ["organisation", "speaker_id", "gender"])
GenerationInfo = namedtuple("GenerationInfo", ["count", "duration"])


class RT09Converter:
    def __init__(self, evaluation_dataset, config):
        self.evaluation_dataset = evaluation_dataset
        self.config = config
        self.min_segment_size = config["converter"]["min_segment_size"]
        self.out_dir = config["converter"]["out_dir"]
        self.max_duration_per_speaker = config["converter"]["max_duration_per_speaker"]
        self.skip_overlapping_segment = config["converter"]["skip_overlapping_segment"]

    def convert(self):
        parser = RT09Parser(self.evaluation_dataset, self.config)
        rt09_elements = parser.parse()

        print(
            "creating a training-set for the dataset: %s with min. segment-size of %dms and a duration per speaker of ca. %dms"
            % (self.evaluation_dataset, self.min_segment_size, self.max_duration_per_speaker))

        base_out_dir = os.path.join(self.out_dir, self.evaluation_dataset)

        if os.path.isdir(base_out_dir):
            shutil.rmtree(base_out_dir)

        os.mkdir(base_out_dir)
        speaker_segments = defaultdict(list)

        print("prepare segmentation per speaker")

        for rt09_element in rt09_elements:
            organisation_name = RT09Converter._get_organisation_name(rt09_element["id"])
            dataset_dir = os.path.join(base_out_dir, organisation_name)

            if not os.path.isdir(dataset_dir):
                os.mkdir(dataset_dir)

            for turn in self._turn_iterator(rt09_element["turns"]):
                speaker = Speaker(organisation_name, turn.speaker, turn.spkrType)

                for file in rt09_element["files"]:
                    speaker_segment = SpeakerSegment(file.replace("sph", "wav"), int(float(turn.startTime) * 1000),
                                                     int(float(turn.endTime) * 1000))
                    speaker_segments[speaker].append(speaker_segment)

        print("start with segmentation...")
        self._generate_speaker_segments(speaker_segments, base_out_dir)
        print("done")

    def _generate_speaker_segments(self, speaker_segments, base_dir):
        current_segment_size = 0.0
        current_segment = AudioSegment.empty()
        segment_generated_per_speaker = defaultdict(lambda: GenerationInfo(0, 0.0))
        overall_duration = 0.0

        gender_distribution = {
            "male": 0,
            "female": 0
        }

        for key, value in speaker_segments.items():
            random.shuffle(value)
            i = 0

            while i < len(value) and segment_generated_per_speaker[key].duration < self.max_duration_per_speaker:
                seg = value[i]

                delta = seg.end - seg.start
                new_size = current_segment_size + delta
                current_segment = current_segment + RT09Converter._cut_audio_segment(seg)
                current_segment_size = new_size

                if new_size > self.min_segment_size:
                    RT09Converter._save_segment(os.path.join(base_dir, key.organisation), key.speaker_id,
                                                segment_generated_per_speaker[key].count, current_segment)

                    segment_generated_per_speaker[key] = GenerationInfo(
                        count=segment_generated_per_speaker[key].count + 1,
                        duration=segment_generated_per_speaker[key].duration + new_size)

                    gender_distribution[key.gender] += 1

                    current_segment = AudioSegment.empty()
                    current_segment_size = 0.0

                i += 1

            overall_duration += segment_generated_per_speaker[key].duration

            print("\tcreated %d segments for speaker (%s,%s) with a duration of %dms" %
                  (segment_generated_per_speaker[key].count, key.organisation, key.speaker_id,
                   segment_generated_per_speaker[key].duration))

        print("\toverall duration is %dms" % overall_duration)
        N = sum(gender_distribution.values())
        print("\tgender-distribution: %1.2f male %1.2f female" % (gender_distribution["male"] / N,
                                                                  gender_distribution["female"] / N))

    @staticmethod
    def _get_organisation_name(dataset_folder):
        return dataset_folder.split("_")[0]

    def _turn_iterator(self, turns):
        if self.skip_overlapping_segment:
            for turn in RT09Converter._skip_overlap_generator(turns):
                yield turn
        else:
            for turn in turns:
                yield turn

    @staticmethod
    def _save_segment(base_dir, speaker_id, idx, audio_segment):
        if not os.path.isdir(base_dir):
            os.mkdir(base_dir)

        speaker_path = os.path.join(base_dir, speaker_id)

        if not os.path.isdir(speaker_path):
            os.mkdir(speaker_path)

        audio_segment.export(os.path.join(speaker_path, "%d.wav" % idx), format="wav")

    @staticmethod
    def _cut_audio_segment(speaker_segment):
        audio = AudioSegment.from_wav(speaker_segment.filename)
        return audio[speaker_segment.start:speaker_segment.end]

    @staticmethod
    def _skip_overlap_generator(turns):
        n = len(turns)
        i = 0

        while i < n:
            curr = turns[i]

            # overlaps the previous turn?
            if i > 0 and turns[i - 1].endTime < curr.startTime:
                if i + 1 < n and turns[i + 1].startTime > curr.endTime:
                    yield curr
                    i += 1
                else:
                    i += 2  # skip also next element
            else:
                i += 1
