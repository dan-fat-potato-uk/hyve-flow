from hyve.config import ExtractorConfig

from pathlib import Path

from textwrap import dedent
from wellies import ToolStore

import pyflow as pf

def get_extraction_config(config: dict) -> dict:
    return {
        "station": {
            "file": str(Path(config["working_dir"]) / config["reference"]),
            "name": config["station_id"],
            "coords": {
                "x": "LisfloodX",
                "y": "LisfloodY",
            },
        },
        "grid": {
            "source": {
                "file": {
                    "path": str(Path(config["working_dir"]) / config["input"]),
                },
            },
            "coords": {
                "x": "lon",
                "y": "lat",
            },
        },
        "output": {
            "file": str(Path(config["working_dir"]) / config["output"]),
        },
    }

class ReanalysisProcessing:
    def __init__(self, config: dict, tools: ToolStore, exec_env: str):
         self.config = config
         self.tools = tools
         self.exec_env = exec_env


    def build_extraction_task(self, config_script, task_args: dict, preprocess: list | str = [], work_dir: str = ".") -> pf.Task:
        extraction_config = {
            **self.config,
            "working_dir": work_dir,
        }

        config = get_extraction_config(extraction_config)

        script = [
            *([preprocess] if isinstance(preprocess, str) else preprocess),
            dedent("""
                mkdir -p $WORKDIR
                cd $WORKDIR
                hyve-extract-timeseries extract.yaml
            """),
        ]

        return pf.Task(
            name="extract_stations",
            variables={"WORKDIR": work_dir},
            script=[
                *config_script(config=config, out_path="extract.yaml"),
                self.tools.load(self.exec_env),
                *script
            ],
            **task_args
        )