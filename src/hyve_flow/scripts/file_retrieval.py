#! /usr/bin/env python3
import logging
import os
import sys
import tarfile
from datetime import date, datetime

import earthkit.data as ekd
import xarray as xr
from annotated_types import Annotated
from conflator import CLIArg
from earthkit.time import Sequence
from pydantic import AfterValidator, Field, ConfigDict, BaseModel

logger = logging.getLogger(__name__)

def parse_ensemble_range(entry) -> list[int]:
    try:
        number_int = int(entry)
        return list(range(number_int + 1))
    except (ValueError, TypeError):
        if "-" in entry:
            start, end = map(int, entry.split("-"))
            return list(range(start, end + 1))
        elif "," in entry:
            return [int(num.strip()) for num in entry.split(",")]
        else:
            raise ValueError(
                "Invalid format for number. Use an integer, a range (e.g., '0-10'), "
                "or a comma-separated list (e.g., '0,1,2')."
            )


def parse_isodate(entry) -> date:
    try:
        return date.fromisoformat(entry)
    except ValueError:
        try:
            return datetime.strptime(entry, "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(entry, "%Y%m%d").date()
            except ValueError:
                raise ValueError(
                    "Invalid date format. Use 'YYYY-MM-DD' or 'YYYYMMDD', or check date.fromisoformat and "
                    f"python={sys.version_info}."
                )


def parse_remapping(entry) -> dict:
    if entry is None:
        return {}
    elif isinstance(entry, dict):
        return entry
    elif isinstance(entry, str):
        remaps = {}
        for pair in entry.split(","):
            try:
                original, new = pair.split(":")
                remaps[original.strip()] = new.strip()
            except ValueError:
                raise ValueError(
                    f"Invalid remapping pair '{pair}'. Use 'original:new' format."
                )
        return remaps
    else:
        raise ValueError("Remapping must be a string or a dictionary.")
    
class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class FileRetrievalConfig(StrictBaseModel):
    target_file = Annotated[
        str,
        CLIArg("--target-file"),
        Field(
            description=(
                "Target file for EFAS data to retrieve. Can contain "
                "template strings using common dataset keys in the name."
            ),
            examples=[
                "HS{reference_date:%Y%m%d}/{valid_date:%Y%m%d}.{number:%d}.dis_stations.nc",
            ],
        ),
    ]
    sequence_key = Annotated[
        str,
        CLIArg("--earthkit-sequence"),
        Field(description="Key to use to retrieve day sequence from earthkit"),
    ] = "ecmwf-4days"
    hindcast_years = Annotated[
        int,
        CLIArg("--hindcast"),
        Field(description="How many years of data to retrieve"),
    ] = 20
    data_source = Annotated[
        str,
        CLIArg("--data-source"),
        Field(description="Which data source to retrieve data from"),
    ] = "ecfs"
    ensemble = Annotated[
        str | int,
        CLIArg("--number"),
        Field(
            description="Number of ensemble members to retrieve",
            examples=[
                "10",
                "0-10",
                "0,1,2,3,4,5,6,7,8,9,10",
            ],
        ),
        AfterValidator(parse_ensemble_range),
    ] = 10
    output_dir = Annotated[
        str,
        CLIArg("--output"),
        Field(description="Where to store the output of this data dowload"),
    ]
    base_date = Annotated[
        str,
        CLIArg("--base-date"),
        Field(
            description="base date for the reforecast reference dates to retrieve.",
            examples=[
                "2023-01-01",
                "20230101",
            ],
        ),
        AfterValidator(parse_isodate),
    ] = None
    bracket_size = Annotated[
        int,
        CLIArg("--bracket-size"),
        Field(
            description=(
                "Size of the bracket, in days, to use to retrieve reference dates, "
                "before and after <base-date>."
            )
        ),
    ] = 4
    overwrite = Annotated[
        bool,
        CLIArg("--overwrite", action="store_true"),
        Field(description="Whether to overwrite existing files or not"),
    ] = False
    remapping = Annotated[
        str | dict | None,
        CLIArg("--remapping"),
        Field(
            description=(
                "Remapping to apply to the data. Can be a string with comma separated remaps pairs,"
                "predefined remapping, or a dictionary with the remapping parameters. "
                "Left-hand side name must exist in the original dataset."
            )
        ),
        AfterValidator(parse_remapping),
    ] = None


def download(config: FileRetrievalConfig):
    sequence = Sequence.from_resource(config.sequence_key)
    if not config.base_date:
        base_date = date.today()
    else:
        base_date = config.base_date
    reference_dates = sequence.bracket(
        base_date, config.date_bracket_size, strict=False
    )

    # Loops over each year to retrieve the reforecast for each year
    merged_output = f"{config.output_dir}/{base_date:%Y%m%d}"
    os.makedirs(merged_output, exist_ok=True)

    for ref_date in reference_dates:
        years = range(ref_date.year - config.hindcast_years, ref_date.year)
        for year in years:
            valid_date = date(year, ref_date.month, ref_date.day)
            outname = f"{merged_output}/dis_stations_{valid_date:%Y%m%d}.nc"
            if os.path.exists(outname) and not config.overwrite:
                print(f"File {outname} already exists, skipping download.")
                continue
            ensemble_files = []
            for number in config.number:
                path = config.target_file.format(
                    reference_date=ref_date,
                    valid_date=valid_date,
                    number=number,
                )
                output_tar = os.path.basename(path)

                # Uses earthkit to retrieve the data
                # Note, this can only be run within ecmwf if data source is "ecfs"
                ds = ekd.from_source(
                    config.data_source,
                    path,
                )

                # Output is a tar so we need to handle this to extract the file
                ds.to_target("file", output_tar)

                # Opens the file and checks if the number of files is expected (1)
                with tarfile.open(output_tar) as tar:
                    files = [m for m in tar.getmembers() if m.isfile()]
                    assert len(files) == 1
                    output_reforecast_file = files[0].name
                    dname = os.path.dirname(
                        os.path.realpath(output_reforecast_file)
                    )
                    os.makedirs(dname, exist_ok=True)
                    # If all is expected, extracts the file in the same directory as it was downloaded
                    extracted = tar.extractfile(files[0])
                    with open(output_reforecast_file, "wb") as f:
                        f.write(extracted.read())
                    ensemble_files.append(output_reforecast_file)
                os.remove(output_tar)

            (
                xr.open_mfdataset(
                    ensemble_files, combine="nested", concat_dim="ensemble"
                )
                .rename(config.remapping)
                .to_netcdf(outname)
            )
