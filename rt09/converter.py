import os
import random
from collections import namedtuple, defaultdict
from .rt09_parser import RT09Parser
from pydub import AudioSegment


SpeakerSegment = namedtuple("SpeakerSegment", ["filename", "start", "end"])
Speaker = namedtuple("Speaker", ["speaker_id", "gender"])


class RT09Converter:
    def __init__(self, config):
        self.config = config
        self.segment_size = config["converter"]["segment_size"]
        self.out_dir = config["converter"]["out_dir"]
        self.max_duration_per_speaker = config["converter"]["max_duration_per_speaker"]
        self.speaker_segments = defaultdict(list)

    def convert(self):
        parser = RT09Parser(self.config)
        rt09_elements = parser.parse()

        rt09_element = rt09_elements[0]
        base_out_dir = os.path.join(self.out_dir, rt09_element["id"])

        for turn in RT09Converter._skip_overlap_generator(rt09_element["turns"]):
            speaker = Speaker(turn.speaker, turn.spkrType)

            for file in rt09_element["files"]:
                speaker_segment = SpeakerSegment(file.replace("sph", "wav"), int(float(turn.startTime) * 1000),
                                                 int(float(turn.endTime) * 1000))
                self.speaker_segments[speaker].append(speaker_segment)

        current_segment_size = 0.0
        current_segment = AudioSegment.empty()
        segment_generated_per_speaker = defaultdict(int)

        for key, value in self.speaker_segments.items():
            random.shuffle(value)
            i = 0

            while i < len(value) and (segment_generated_per_speaker[key] * self.segment_size) < self.max_duration_per_speaker:
                seg = value[i]

                delta = seg.end - seg.start
                new_size = current_segment_size + delta

                if new_size < self.segment_size:
                    current_segment = current_segment + RT09Converter._cut_audio_segment(seg)
                    current_segment_size = new_size
                    i += 1
                else:
                    if new_size > self.segment_size:
                        current_segment = current_segment + AudioSegment.silent(self.segment_size - current_segment_size)
                    else:
                        i += 1

                    RT09Converter._save_segment(base_out_dir, key.speaker_id, segment_generated_per_speaker[key],
                                                current_segment)

                    segment_generated_per_speaker[key] += 1
                    current_segment = AudioSegment.empty()
                    current_segment_size = 0.0

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
                    i += 2 #skip also next element
            else:
                i += 1