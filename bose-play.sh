#!/bin/zsh

cd $(dirname "$0")
source bose.cfg

# Check argument was passed.
if [[ -z "$1" ]]
then
  echo "Please pass a media file to play."
  exit 1
fi

src=$1

# If source was Youtube video, download it first.
if [[ "$src" == http* ]]
then
  rm -f /tmp/bose-youtube-dl
  youtube-dl "$src" -f bestaudio -o /tmp/bose-youtube-dl
  src="/tmp/bose-youtube-dl"
fi

# Ensure Bose is not playing anything right now.
./bose-key.exp stop

# Clear any previous audio files.
rm -f $temp_audiofile

# Convert to mp3 so Bose understands.
$converter -i "$src" -metadata album="PC" -codec:a libmp3lame -qscale:a 2 $temp_audiofile

# Instruct Bose to play.
./bose-key.exp preset_$preset
./bose-key.exp prev

