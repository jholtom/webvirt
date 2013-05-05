#!/bin/bash

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: adduser.sh [database] [username]"
    exit
fi

if [ ! -f "$1" ]; then
    echo "The specified database does not exist!"
    echo "Please create it and try again."
    exit
fi

echo -n "New Password: "
read -s password
echo

hash=`python2 -c "import bcrypt; print(bcrypt.hashpw('$password', bcrypt.gensalt()))"`
sqlite3 $1 "INSERT INTO users VALUES('$2', '$hash')"
echo "Done"
