from rt09.converter import RT09Converter
from rt09.util import RT09Config
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts the RT-09 dataset to a TIMIT like dataset, which can be used in the ZHAW deep voice suite")

    parser.add_argument("evaluation_dataset", metavar="e",
                        help="the evaluation dataset. this dataset is excluded from the training-set")

    args = parser.parse_args()
    config = RT09Config.load_config()

    converter = RT09Converter(evaluation_dataset=args.evaluation_dataset, config=config)
    converter.convert()
