#!/bin/bash
cd "$(dirname $0"
curl http://localhost:8000/v1/audio/transcriptions -F "file=@audio.wav" -F "stream=true"
