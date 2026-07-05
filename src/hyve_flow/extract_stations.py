#! /usr/bin/env python3
import logging as log
from pathlib import Path
from textwrap import dedent

from annotated_types import Annotated
from conflator import CLIArg, Conflator, ConfigModel
from hyve.config import ExtractorConfig
from hyve.extraction import extractor
from pydantic import Field

import pyflow as pf

# Configure logging
log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ExtractStationConfig(ConfigModel):

    """Configuration for extracting stations from reanalysis files."""

    working_dir: Annotated[
        str, CLIArg("--working-dir"), Field(description="Working directory to look for paths from")
    ]
    reference: Annotated[
        str, CLIArg("--reference"), Field(description="Outlets file for reference")
    ]
    input: Annotated[
        str,
        CLIArg("--input"),
        Field(
            description="Reanalysis directory containing reanalysis files to extract stations from"
        ),
    ]
    output: Annotated[
        str,
        CLIArg("--output"),
        Field(description="Output directory for extracted stations"),
    ]
    station_id: Annotated[
        str,
        CLIArg("--station-id"),
        Field(
            description="The station identifier used in the reference file (defaults to 'station_id')"
        ),
    ] = "station_id"
    overwrite: Annotated[
        bool,
        CLIArg("--overwrite"),
        Field(description="Whether to overwrite existing files or not"),
    ] = False


def getConfig(app_config: ExtractStationConfig, input_file: str, output_file: str) -> ExtractorConfig:
    return ExtractorConfig(
        **{
            "station": {
                "file": str(Path(app_config.working_dir) / app_config.reference),
                "name": app_config.station_id,
                "coords": {"x": "LisfloodX", "y": "LisfloodY"},
            },
            "grid": {
                "source": {"file": {"path": input_file}},
                "coords": {
                    "x": "lon",
                    "y": "lat",
                },
            },
            "output": {"file": output_file},
        }
    )

def build_extraction_task(extraction_config: dict, config_script, preprocess: list | str = [], work_dir: str = ".") -> pf.Task:
    config = {
        **extraction_config,
        "working-dir": work_dir,
    }

    script = [*config_script(config=config, out_path="extract.yaml")]

    if isinstance(preprocess, str):
        script.append(preprocess)
    else:
        script.extend(preprocess)
    script.append(dedent("""
        cd $WORKDIR
        hyve-extract-stations -f extract.yaml
    """))

    return pf.Task(
        name="extract_stations",
        variables={"WORKDIR": work_dir},
        script=script,
        submit_arguments="large",
    )


def main():
    config = Conflator(app_name="reanalysis_extraction", model=ExtractStationConfig).load()

    try:
        directory = Path(config.working_dir) / config.input
        output_path = Path(config.working_dir) / config.output

        for file in directory.glob("*.nc"):
            # Get extraction config
            input_file = f"{directory}/{file.name}"
            output_file = f"{output_path}/dis_stations_{file.name}"

            if Path(output_file).exists() and not config.overwrite:
                print(f"{file.name} already exists, skipping...")
            else:
                print(f"Extracting {input_file} to {output_file}")
                extractionConfig = getConfig(config, directory, output_file)

                # Now extract the stations
                extractor(extractionConfig)
    except Exception as e:
        log.error(f"Error during execution: {e}")
        raise

if __name__ == "__main__":
    main()