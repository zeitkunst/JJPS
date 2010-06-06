#!/bin/bash

if /usr/bin/test "$#" -ne 1; then
    echo "Usage: bash build.sh versionNumber"
    exit 1
fi

XPI_NAME=JJPS.$1.xpi

zip -r $XPI_NAME . -x "*.git/*" \*.xpi

#cp $XPI_NAME ../MAICgregatorServer/static
#svn add ../MAICgregatorServer/static/$XPI_NAME

openssl sha1 $XPI_NAME
