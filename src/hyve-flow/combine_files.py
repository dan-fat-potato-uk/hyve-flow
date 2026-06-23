#! /usr/bin/env python3
import glob
import os
import shutil
from pathlib import Path

import xarray as xr
from annotated_types import Annotated
from conflator import CLIArg
from pydantic import Field, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CombineFileConfig(StrictBaseModel):
    reference_file: Annotated[
        str,
        CLIArg("--reference-file"),
        Field(
            description="Archived data set to append retrieved data sets to"
        ),
    ]
    extracted_stations: Annotated[
        str,
        CLIArg("--stations-dir"),
        Field(description="Path to extracted stations data"),
    ]
    store: Annotated[
        str,
        CLIArg("--store"),
        Field(description="Data set to append all retrieved data files to"),
    ]
    file_pattern: Annotated[
        str,
        CLIArg("--pattern"),
        Field(
            description="Extracted station file pattern to search for",
            examples=["station_file_*.nc"],
        ),
    ]

def combine(config: CombineFileConfig):
    shutil.copy(config.reference_file, config.store)

    files = sorted(
        glob.glob(os.path.join(config.extracted_stations, config.file_pattern))
    )

    print(f"Found files: {[Path(p).name for p in files]}")

    ref_df = xr.open_dataset(config.store).assign_coords(
        station=lambda ds: ds.station.astype("<U6")
    )

    all_ds = [
        (
            xr.open_dataset(ff).assign_coords(
                station=lambda ds: ds.station.astype("<U6")
            )
        )
        for ff in files
    ]

    merged = xr.concat([ref_df] + all_ds, dim="time").sortby("time")

    backup_store = f"{config.store}.bak"
    if os.path.exists(backup_store):
        os.remove(backup_store)
    os.rename(config.store, backup_store)

    merged.to_netcdf(config.store)


