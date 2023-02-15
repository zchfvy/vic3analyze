#!/usr/bin/env zsh
# Shell script for doing preprocessing to msgpack on an archive of replays
# Usage: process_archive.sh INPUT OUTPUT

ARC_IN=$1
ARC_OUT=$2
WORKDIR='/tmp/v3tmp'

V3TMP=$(mktemp -d -p $WORKDIR)
# trap 'rm -rf -- "$V3TMP"' EXIT
mkdir -p $V3TMP/files_in
mkdir -p $V3TMP/files_out

FILES="$(7z l -ba $ARC_IN | sed -nE 's/.* (\S+.v3).*/\1/p' | sort)"
echo "Found archive with "$(echo $FILES | wc -l)" files to process"

if [ -f $ARC_OUT ]; then
    echo "Found existing output archive"
    DONE_FILES="$(7z l -ba $ARC_OUT | sed -nE 's/.* (\S+.v3).*/\1\n/p' | sort)"
    echo "Found $(echo $DONE_FILES | wc -l) complete samples"
    FILES=$(comm -23 <(echo $FILES) <(echo $DONE_FILES))
    echo "Will process only $(echo $FILES | wc -l) incomplete samples"
fi

# ==== Actual Process Starts HERE ====

# This extracts the input archive to a temp dir
7z x $ARC_IN -o$V3TMP/files_in

# This runs the process to convert extracted files to msgpack
parallel --eta ./rakaly json $V3TMP/files_in/{} | json2msgpack > $V3TMP/files_out/{}.msgpack ::: $FILES

# This saves the converted files to a new archive
7z a -tzip -mm=LZMA $ARC_OUT $V3TMP/files_out/*
