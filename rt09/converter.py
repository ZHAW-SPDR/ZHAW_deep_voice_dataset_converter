import os
import random
import shutil
import numpy as np
from collections import namedtuple, defaultdict
from .rt09_parser import RT09Parser
from pydub import AudioSegment

SpeakerSegment = namedtuple("SpeakerSegment", ["filename", "start", "end"])
Speaker = namedtuple("Speaker", ["organisation", "speaker_id", "gender"])
GenerationInfo = namedtuple("GenerationInfo", ["count", "duration"])


class RT09Converter:
    def __init__(self, evaluation_dataset, config):
        self.config = config
        self.evaluation_dataset = evaluation_dataset
        self.out_dir = config["converter"]["out_dir"]
        self.min_segment_size = config["converter"]["min_segment_size"]
        self.use_normalized_audio = config["data"]["use_normalized_audio"]
        self.max_duration_per_speaker = config["converter"]["max_duration_per_speaker"]
        self.skip_overlapping_segment = config["converter"]["skip_overlapping_segment"]

        self.tolerance = 0.1
        self.tolerance_segment_size = (1.0 + self.tolerance) * self.min_segment_size
        self.max_duration_per_speaker_tolerance = (1.0 - self.tolerance) * self.max_duration_per_speaker

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
                    speaker_segment = SpeakerSegment(self._get_filename(file), int(float(turn.startTime) * 1000),
                                                     int(float(turn.endTime) * 1000))
                    speaker_segments[speaker].append(speaker_segment)

        print("start with segmentation...")
        speaker_to_exclude = self._generate_speaker_segments(speaker_segments, base_out_dir)
        print("done")

        RT09Converter._create_speaker_list_file(base_out_dir, speaker_segments, speaker_to_exclude)
        print("created speaker file")

    def _generate_speaker_segments(self, speaker_segments, base_dir):
        current_segment_size = 0.0
        current_segment = AudioSegment.empty()
        segment_generated_per_speaker = defaultdict(lambda: GenerationInfo(0, 0.0))
        overall_duration = 0.0
        segment_sizes = []

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

                if new_size <= self.tolerance_segment_size:
                    current_segment = current_segment + RT09Converter._cut_audio_segment(seg)
                    current_segment_size = new_size

                    if new_size > self.min_segment_size:
                        RT09Converter._save_segment(
                            os.path.join(base_dir, key.organisation),
                            "%s_%s" % (key.organisation, key.speaker_id),
                            segment_generated_per_speaker[key].count, current_segment)

                        segment_generated_per_speaker[key] = GenerationInfo(
                            count=segment_generated_per_speaker[key].count + 1,
                            duration=segment_generated_per_speaker[key].duration + new_size)

                        gender_distribution[key.gender] += 1

                        current_segment = AudioSegment.empty()
                        current_segment_size = 0.0
                        segment_sizes.append(new_size)

                i += 1

            overall_duration += segment_generated_per_speaker[key].duration

            print("\tcreated %d segments for speaker (%s,%s) with a duration of %dms" %
                  (segment_generated_per_speaker[key].count, key.organisation, key.speaker_id,
                   segment_generated_per_speaker[key].duration))

        speakers_to_exclude = [k for k, v in segment_generated_per_speaker.items()
                               if v.duration <= self.max_duration_per_speaker_tolerance]

        print("\tspeakers to exclude [%s]" % ", ".join(map(lambda speaker: speaker.speaker_id, speakers_to_exclude)))

        print("\toverall duration is %dms" % overall_duration)
        N = sum(gender_distribution.values())
        print("\tgender-distribution: %1.2f male %1.2f female" % (gender_distribution["male"] / N,
                                                                  gender_distribution["female"] / N))
        durations = np.array(segment_sizes)
        print("\tsegment-sizes stats: mean: %.3f stddev: %.3f min: %f max: %f"
              % (durations.mean(), durations.std(), durations.min(), durations.max()))

        return speakers_to_exclude

    def _get_filename(self, filename):
        if self.use_normalized_audio:
            return filename.replace(".sph", "_normalized.wav")

        return filename.replace(".sph", ".wav")

    @staticmethod
    def _create_speaker_list_file(base_dir, speaker_segments, exclude):
        filtered_speakers = [speaker for speaker in speaker_segments.keys()
                             if speaker not in exclude]

        with open(os.path.join(base_dir, "speakers_rt09.txt"), mode="w") as speaker_file:
            speaker_file.writelines(
                map(lambda key: "%s_%s\n" % (key.organisation, key.speaker_id), sorted(filtered_speakers))
            )

    @staticmethod
    def _get_organisation_name(dataset_folder):
        return dataset_folder.split("_")[0]

    def _turn_iterator(self, turns):
        if self.skip_overlapping_segment:
            for turn in RT09Converter._skip_overlap_generator(turns):
                yield turn
        else:
            for turn in turns:
                delta = int((float(turn.endTime) - float(turn.startTime)) * 1000)

                if delta <= self.tolerance_segment_size:
                    yield turn
                else:
                    print("skipped turn with length %d" % delta)

    @staticmethod
    def _save_segment(base_dir, speaker_id, idx, audio_segment):
        if not os.path.isdir(base_dir):
            os.mkdir(base_dir)

        speaker_path = os.path.join(base_dir, speaker_id)

        if not os.path.isdir(speaker_path):
            os.mkdir(speaker_path)

        audio_segment.export(os.path.join(speaker_path, "%d_RIFF.WAV" % idx), format="wav")

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
