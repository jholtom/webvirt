#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: setupdb.sh [database]"
    exit
fi

if [ ! -f "$1" ]; then
    echo "The specified file does not exist!"
    echo "SQLite3 will try to create it for you..."
fi

sqlite3 "$1" "CREATE TABLE users(username, password);"
sqlite3 "$1" "CREATE TABLE sessions(username, sid, ip);"
echo "Done"
