# Playlists Creator

A python script which:
- connects to the bose sound system via telnet
- watches the IR remote keys
- adds the currently played file to a like or dislike playlist

## Requirements
- a local DNLP server, for example miniDNLP
- a shared folder for the playlist files

## Config
Copy the file config_template.cfg to config.cfg and insert the ip address of your bose system...

## Start
Run the following command to start it:
``python playlist-creator-service.py``

tested with python 2.7
