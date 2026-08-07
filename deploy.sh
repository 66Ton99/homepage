#!/usr/bin/env bash
# Deploy site/ to the nginx web root on nixos-micro.
#
#   ./deploy.sh            rsync site/ -> /var/www/66ton99.org.ua/
#   ./deploy.sh --nixos    also copy nixos/site.nix and nixos-rebuild switch
#
# site/ mirrors the web root exactly, so what is in git is what is served.

set -euo pipefail

HOST=nixos-micro
WEBROOT=/var/www/66ton99.org.ua
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> rsync site/ -> $HOST:$WEBROOT"
rsync -avz --delete \
  --exclude '.DS_Store' \
  --exclude 'index.html.bak.*' \
  --rsync-path="sudo rsync" \
  "$HERE/site/" "$HOST:$WEBROOT/"

echo "==> fixing ownership"
ssh "$HOST" "sudo chown -R nginx:nginx $WEBROOT"

if [[ "${1:-}" == "--nixos" ]]; then
  echo "==> copying nixos/site.nix"
  scp "$HERE/nixos/site.nix" "$HOST:/tmp/site.nix"
  ssh "$HOST" 'sudo cp /tmp/site.nix /etc/nixos/site.nix && rm /tmp/site.nix'
  echo "==> nixos-rebuild switch"
  ssh "$HOST" 'sudo nixos-rebuild switch'
fi

echo "==> smoke test"
for url in \
  https://66ton99.org.ua/ \
  https://66ton99.org.ua/awg-to-amps \
  https://66ton99.org.ua/uk/awg-to-amps \
  https://66ton99.org.ua/robots.txt \
  https://66ton99.org.ua/sitemap.xml \
  https://66ton99.org.ua/og-awg-to-amps.png
do
  printf '  %-46s %s\n' "${url#https://66ton99.org.ua}" \
    "$(curl -sS -o /dev/null -w '%{http_code}' "$url")"
done

echo "done."
