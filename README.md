# dicomfinder

Recursively find, copy and anonymize all DICOM datasets in a folder.

## Installation

Either install set up dependencies in a new virtual environment, or just use uv:

```
uv run main.py [--list-only] <src> <dest>
```

The program will recursively traverse and identify all DICOM series in `src`, copy them
to `dest` and anonymize the dataset (DICOM fields referenced in the 2023e DICOM standard).