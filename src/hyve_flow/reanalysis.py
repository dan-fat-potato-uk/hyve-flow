from hyve.config import ExtractorConfig

from pathlib import Path

from textwrap import dedent
from wellies import ToolStore

import pyflow as pf


class ReanalysisProcessing:
    def __init__(self, config: dict, tools: ToolStore, exec_env: str):
         self.config = config
         self.tools = tools
         self.exec_env = exec_env


    def build_extraction_task(self, config_script, task_args: dict, preprocess: list | str = [], work_dir: str = ".") -> pf.Task:

        script = [
            *([preprocess] if isinstance(preprocess, str) else preprocess),
            dedent("""
                mkdir -p $WORKDIR
                cd $WORKDIR
                hyve-extract-timeseries extract.yaml
            """),
        ]

        task_args.setdefault("name", "extract_stations")

        return pf.Task(
            variables={"WORKDIR": work_dir},
            script=[
                self.tools.load(self.exec_env),
                *config_script(config=self.config.extraction, output_file="extract.yaml", work_dir=work_dir),
                *script
            ],
            **task_args
        )
