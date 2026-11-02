#!/usr/bin/env bash
# Zagon na Linux stagingu. Ne beleži okolja procesov ali vsebin zahtev.
set -euo pipefail
output="${1:?Podaj izhodno mapo zagona}"
interval="${2:-10}"
mkdir -p "$output"
printf 'utc,load1,mem_total_kb,mem_available_kb,disk_available_kb\n' > "$output/host.csv"
while true; do
  utc=$(date -u +%FT%TZ)
  load=$(cut -d' ' -f1 /proc/loadavg)
  total=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
  available=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
  disk=$(df -Pk "$output" | awk 'NR==2 {print $4}')
  printf '%s,%s,%s,%s,%s\n' "$utc" "$load" "$total" "$available" "$disk" >> "$output/host.csv"
  if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    docker stats --no-stream --format '{{json .}}' | while IFS= read -r line; do
      printf '{"utc":"%s","stats":%s}\n' "$utc" "$line" >> "$output/containers.jsonl"
    done
    docker ps -a --format '{{json .}}' | while IFS= read -r line; do
      printf '{"utc":"%s","container":%s}\n' "$utc" "$line" >> "$output/container-state.jsonl"
    done
  fi
  sleep "$interval"
done
