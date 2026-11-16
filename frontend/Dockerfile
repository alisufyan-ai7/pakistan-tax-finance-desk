# Public SYNTHETIC dashboard preview only. No API, database or personal records.
# This image intentionally includes only four allowlisted fictional frontend files.
FROM nginxinc/nginx-unprivileged:stable-alpine

COPY nginx.railway.conf /etc/nginx/conf.d/default.conf
COPY index.html ui.css ui.mjs demo-data.mjs /usr/share/nginx/html/

EXPOSE 8080
