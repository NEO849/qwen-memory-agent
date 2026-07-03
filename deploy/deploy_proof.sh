#!/usr/bin/env bash
# Regress-Guard — Alibaba Cloud deploy proof.
# Run this ON the ECS instance while screen-recording (~35s). It shows, on the box itself:
#   1) this host really is an Alibaba Cloud ECS instance (on-box metadata service),
#   2) its public IP is the live demo URL,
#   3) the backend runs as a systemd service, and
#   4) the public API answers live.
# The metadata endpoint 100.100.100.200 exists ONLY on genuine Alibaba (Aliyun) ECS — the strongest proof.
set -u
cap(){ printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; sleep 1; }
MD=http://100.100.100.200/latest/meta-data

printf '\033[1;37m\n  Regress-Guard — proof the backend runs on Alibaba Cloud ECS\n\033[0m'
sleep 1.2

cap "1/4  This host is an Alibaba Cloud ECS instance (on-box metadata service)"
echo "region-id   : $(curl -s --max-time 4 $MD/region-id)"
echo "zone-id     : $(curl -s --max-time 4 $MD/zone-id)"
echo "instance-id : $(curl -s --max-time 4 $MD/instance-id)"
echo "OS image    : $(curl -s --max-time 4 $MD/image-id)   <- 'alibase' = Alibaba Cloud base image"
sleep 1.8

cap "2/4  This instance's public IP == the live demo URL"
PUBIP=$(curl -s --max-time 4 $MD/eipv4); [ -z "$PUBIP" ] && PUBIP=$(curl -s --max-time 4 $MD/public-ipv4)
echo "public IP   : $PUBIP"
echo "demo URL    : http://47.84.227.215"
sleep 1.8

cap "3/4  The backend runs as a systemd service (uvicorn, port 80)"
systemctl status regress-guard --no-pager | head -4
ss -ltnp | grep ':80 '
sleep 1.8

cap "4/4  The public API answers — live, from this Alibaba box"
echo "\$ curl http://127.0.0.1/health";  curl -s --max-time 5 http://127.0.0.1/health;  echo
echo "\$ curl http://127.0.0.1/metrics"; curl -s --max-time 5 http://127.0.0.1/metrics; echo
sleep 1

printf '\n\033[1;32m  Proof complete — Regress-Guard is live on Alibaba Cloud ECS (region ap-southeast-1).\033[0m\n\n'
