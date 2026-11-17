# Public SYNTHETIC dashboard preview only. No API, database or personal records.
# This image includes only explicitly allowlisted public fictional frontend/PWA assets.
FROM nginxinc/nginx-unprivileged:stable-alpine

# Render ONLY PREVIEW_INTERNAL_TOKEN; preserve nginx built-ins such as $uri.
# The secret is held in Railway service variables and never sent to the browser.
ENV NGINX_ENVSUBST_FILTER="^PREVIEW_INTERNAL_TOKEN$"
COPY nginx.railway.conf /etc/nginx/templates/default.conf.template
COPY index.html ui.css ui.mjs demo-data.mjs document-inbox.mjs /usr/share/nginx/html/
COPY manifest.webmanifest sw.js pwa.mjs pwa.css /usr/share/nginx/html/
COPY icons/ /usr/share/nginx/html/icons/

EXPOSE 8080
