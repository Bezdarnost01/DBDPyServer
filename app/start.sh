#!/bin/bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:443 --keyfile /etc/letsencrypt/live/dbdclub.live/privkey.pem --certfile /etc/letsencrypt/live/dbdclub.live/fullchain.pem
