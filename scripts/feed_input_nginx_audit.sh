#!/bin/sh
# Feed input adoption audit — nginx access-log aggregation (READ-ONLY, run as root on the web host).
#   ssh <host> 'sudo sh -s' < scripts/feed_input_nginx_audit.sh
# 출력은 경로·상태·건수 집계뿐. IP·UA·쿼리스트링·id 는 출력하지 않는다(id 는 {id} 로 마스킹).
cd /var/log/nginx
echo "--- ALL write-method api paths (14d): count method path status"
zcat -f access.log* | grep -E '"(POST|PUT|PATCH|DELETE) /api' | awk '{print $6, $7, $9}' | sed -E 's#/[0-9a-f-]{36}#/{id}#g; s#\?[^ ]*##' | sort | uniq -c | sort -rn | head -40
echo "--- GET /api/v1/farms/{id}/* paths top 25 (what logged-in users actually read)"
zcat -f access.log* | grep -E '"GET /api/v1/farms/' | awk '{print $7}' | sed -E 's#/[0-9a-f-]{36}#/{id}#g; s#\?[^ ]*##' | sort | uniq -c | sort -rn | head -25
echo "--- distinct days with any POST to /api/v1/farms/{id}/(events|farrowings|matings|weanings|sync|feed-records)"
zcat -f access.log* | grep -E '"POST /api/v1/farms/[0-9a-f-]{36}/' | awk '{print substr($4,2,11), $7}' | sed -E 's#/[0-9a-f-]{36}#/{id}#g; s#\?[^ ]*##' | sort | uniq -c
echo "--- log span (first/last date, total lines)"
zcat -f access.log* | awk '{print substr($4,2,11)}' | sort -t/ -k3,3n -k2,2M -k1,1n | sed -n '1p;$p'
zcat -f access.log* | wc -l
echo "--- feed-records API hits: method status count"
zcat -f access.log* | grep 'feed-records' | awk '{print $6, $9}' | sort | uniq -c
echo "--- feed-records hits per day"
zcat -f access.log* | grep 'feed-records' | awk '{print substr($4,2,11)}' | sort | uniq -c
echo "--- web page GET /feed hits (html navigations)"
zcat -f access.log* | grep -E '"GET /feed(\?[^ ]*)? HTTP' | awk '{print $9}' | sort | uniq -c
echo "--- web page /feed chunk loads"
zcat -f access.log* | grep -E 'chunks/app/\(app\)/feed/' | awk '{print $9}' | sort | uniq -c
echo "--- POST /api/* paths (ids masked) top 15"
zcat -f access.log* | grep '"POST /api' | awk '{print $7}' | sed -E 's#/[0-9a-f-]{36}#/{id}#g; s#\?.*##' | sort | uniq -c | sort -rn | head -15
echo "--- other (app) page chunk loads top 15 (discoverability baseline)"
zcat -f access.log* | grep -oE 'chunks/app/\(app\)/[a-z/-]+/page' | sort | uniq -c | sort -rn | head -15
echo "--- 2xx POST feed-records (any at all?)"
zcat -f access.log* | grep 'feed-records' | grep '"POST' | awk '$9 ~ /^2/' | wc -l
