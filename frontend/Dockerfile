# Public SYNTHETIC dashboard preview only. No API, database or personal records.
# This image intentionally includes only four allowlisted fictional frontend files.
FROM nginxinc/nginx-unprivileged:stable-alpine

# Render ONLY PREVIEW_INTERNAL_TOKEN; preserve nginx built-ins such as $uri.
# The secret is held in Railway service variables and never sent to the browser.
ENV NGINX_ENVSUBST_FILTER="^PREVIEW_INTERNAL_TOKEN$"
COPY nginx.railway.conf /etc/nginx/templates/default.conf.template
COPY index.html ui.css ui.mjs demo-data.mjs /usr/share/nginx/html/

EXPOSE 8080
