from rt09.converter import RT09Converter
from rt09.util import RT09Config


if __name__ == '__main__':
    config = RT09Config.load_config()

    converter = RT09Converter(config)
    converter.convert()
