#! /usr/bin/env python3
import logging as log
from pathlib import Path

from annotated_types import Annotated
from conflator import CLIArg
from hyve.config import ExtractorConfig
from hyve.extraction import extractor
from pydantic import Field, ConfigDict, BaseModel

# Configure logging
log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ExtractStationConfig(StrictBaseModel):

    """Configuration for extracting stations from reanalysis files."""

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
                "file": app_config.reference,
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


def extract(config: ExtractStationConfig):

    try:
        directory = Path(config.input)

        for file in directory.glob("*.nc"):
            # Get extraction config
            input_file = f"{config.input}/{file.name}"
            output_file = f"{config.output}/dis_stations_{file.name}"

            if Path(output_file).exists() and not config.overwrite:
                print(f"{file.name} already exists, skipping...")
            else:
                print(f"Extracting {input_file} to {output_file}")
                extractionConfig = getConfig(config, input_file, output_file)

                # Now extract the stations
                extractor(extractionConfig)
    except Exception as e:
        log.error(f"Error during execution: {e}")
        raise

