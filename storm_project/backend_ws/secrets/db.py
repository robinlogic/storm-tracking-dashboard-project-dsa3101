# backend_ws/db.py
import mysql.connector
import os

#DB_CONFIG = {
#    "host": "cloudsql-proxy", #change to "host.docker.internal" if using dockerfile else 127.0.0.1
#    "user": "robin",
#    "password": "Easy2000!",
#    "database": "storm_retrieval",
#    "port": 3306
#}

#def get_conn():
#    return mysql.connector.connect(**DB_CONFIG)

# for use after yaml file is ready)
# import os
# import mysql.connector

DB_CONFIG = {
 "host": os.getenv("DB_HOST", "cloudsql-proxy"),
 "port": int(os.getenv("DB_PORT", 3306)),
 "user": os.getenv("DB_USER", "authorised-user"),
 "password": os.getenv("DB_PASS", "Easy2000!"),
 "database": os.getenv("DB_NAME", "storm_retrieval")
}

def get_conn():
 return mysql.connector.connect(**DB_CONFIG)



