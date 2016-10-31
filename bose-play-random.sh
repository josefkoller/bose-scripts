#!/bin/zsh

cd $(dirname "$0")
source bose.cfg

file=$(find $local_media_directory -name \*.mp3 | shuf -n 1 | xargs -0 echo)

echo "playing: $file"
./bose-play.sh "$file"
