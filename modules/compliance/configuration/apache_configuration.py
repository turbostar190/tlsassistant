import os
from pathlib import Path

from apacheconfig import make_loader

from modules.compliance.configuration.configuration_base import ConfigurationMaker


class ApacheConfiguration(ConfigurationMaker):

    def __init__(self, file: Path = None):
        super().__init__("apache")
        self._string_to_add = ""
        if file:
            self._load_conf(file)

    # Borrowing this function from Configuration for testing purposes
    def _load_conf(self, file: Path):
        """
        Internal method to load the apache configuration file.

        :param file: path to the configuration file
        :type file: str
        """
        with make_loader() as loader:
            self.configuration = loader.load(str(file.absolute()))

    def _load_template(self):
        with open(self._config_template_path, "r") as f:
            self._template = f.read()

    def add_configuration_for_field(self, field, field_rules, data, columns, guideline, target=None):
        config_field = self.mapping.get(field, None)
        name_index = columns.index("name")
        level_index = columns.index("level")
        condition_index = columns.index("condition")
        self._output_dict[field] = {}

        if not config_field:
            # This field isn't available with this configuration
            return

        tmp_string = config_field + " "
        field_rules = self._specific_rules.get(field, field_rules)

        for entry in data:
            condition = ""
            if isinstance(entry, dict):
                name = entry["entry"][name_index]
                level = entry["level"]
                guideline = entry["source"]
                if guideline in entry["entry"]:
                    guideline_pos = entry["entry"].index(guideline)
                    # to get the condition for the guideline I calculate guideline's index and then search it near it
                    step = len(columns)
                    guideline_counter = guideline_pos // step
                    condition = entry["entry"][condition_index + guideline_counter * step]
            else:
                name = entry[name_index]
                level = entry[level_index]
                condition = entry[condition_index]

            if target and target.replace("*", "") not in name:
                continue

            replacements = field_rules.get("replacements", [])
            for replacement in replacements:
                name = name.replace(replacement, replacements[replacement])
            tmp_string += self._get_string_to_add(field_rules, name, level, config_field)
            if self._output_dict[field].get(name):
                if condition:
                    index = len(self.conditions_to_check)
                    self.conditions_to_check[index] = {
                        "columns": columns,
                        "data": data,
                        "expression": condition,
                        "field": config_field,
                        "guideline": guideline,
                        "level": level
                    }
                self._output_dict[field][name]["guideline"] = guideline

        if tmp_string and tmp_string[-1] == ":":
            tmp_string = tmp_string[:-1]
        # this check prevents adding a field without any value
        if len(tmp_string) != len(config_field) + 1:
            self._string_to_add += "\n" + tmp_string

    def remove_field(self, field):
        lines = self._string_to_add.splitlines()
        to_remove = []
        for line in lines:
            if line.strip().startswith(field):
                to_remove.append(line)
        for line in to_remove:
            lines.remove(line)
        self._string_to_add = os.sep.join(lines)

    def _write_to_file(self):
        if not os.path.isfile(self._config_template_path):
            raise FileNotFoundError("Invalid template file")

        with open(self._config_output, "w") as f:
            f.write(self._template + self._string_to_add)
