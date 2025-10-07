#!/bin/bash
export KMP_DUPLICATE_LIB_OK=TRUE
source venv/bin/activate
python test_single_file.py
