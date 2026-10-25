#!/usr/bin/env bash
# Can this machine reach each source? Resolves the audio stream with yt-dlp, then fetches
# only the first 64 KB of it. No full downloads. Usage: geo_test.sh <yt-dlp command...>
YTDLP=("$@")
urls=(
 "VOD-RTVE-Play-La-Revuelta|https://www.rtve.es/play/videos/la-revuelta/programa-22-10-2026-pedro-sanchez/17279095/"
 "YT-PP|https://www.youtube.com/watch?v=xarmHmlObfc"
 "YT-Moncloa|https://www.youtube.com/watch?v=W36hgLBgn4E"
 "YT-Antena3-Noticias|https://www.youtube.com/watch?v=9nUiibroigM"
 "YT-RTVE-Noticias|https://www.youtube.com/watch?v=eAYbm84Ddps"
 "YT-laSexta|https://www.youtube.com/watch?v=RMvlzVIeAc0"
 "LIVE-RTVE-La1|https://www.rtve.es/play/videos/directo/canales-lineales/la-1/"
 "LIVE-RTVE-24h|https://www.rtve.es/play/videos/directo/canales-lineales/24h/"
 "LIVE-Antena3|https://www.atresplayer.com/directos/antena3/"
 "LIVE-laSexta|https://www.atresplayer.com/directos/lasexta/"
 "LIVE-Telecinco|https://www.mitele.es/directo/telecinco/"
 "LIVE-Cuatro|https://www.mitele.es/directo/cuatro/"
)
echo "ip: $(curl -s --max-time 5 https://ipinfo.io/country) $(curl -s --max-time 5 https://ipinfo.io/ip)"
for x in "${urls[@]}"; do
  name=${x%%|*}; url=${x#*|}
  out=$(timeout 90 "${YTDLP[@]}" -q --no-warnings -f "bestaudio/best" -g "$url" 2>&1 | head -3)
  stream=$(echo "$out" | grep -m1 '^http')
  if [ -z "$stream" ]; then
    echo "$name | RESOLVE FAIL | $(echo "$out" | tr '\n' ' ' | cut -c1-160)"; continue
  fi
  code=$(curl -sL -o /dev/null -w "%{http_code} %{size_download}B" --max-time 20 -r 0-65535 "$stream")
  echo "$name | resolved | stream fetch: $code"
done
