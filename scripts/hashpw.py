#!/usr/bin/env python2

import bcrypt
import sys

try:
    password = sys.argv[1]
    print bcrypt.hashpw(password, bcrypt.getsalt())
except:
    sys.stderr.write("Please specify a password\n")
