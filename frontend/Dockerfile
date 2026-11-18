# Public SYNTHETIC dashboard preview only. No API, database or personal records.
# This image includes only explicitly allowlisted public fictional frontend/PWA assets.
FROM nginxinc/nginx-unprivileged:stable-alpine

# Render three explicit variables only; preserve nginx built-ins such as $uri.\n# Missing owner flags/token keep all owner paths closed (404 or 503).
# The secret is held in Railway service variables and never sent to the browser.
ENV NGINX_ENVSUBST_FILTER="^(PREVIEW_INTERNAL_TOKEN|P1AK_OWNER_INGRESS_ENABLED|P1AO_GOOGLE_INGRESS_ENABLED|P1AP_DOCUMENTS_INGRESS_ENABLED|P1Q_PRIVATE_GATEWAY_SHARED_TOKEN)$"
# Both new owner inputs MUST have a defined safe default. Without these
# values envsubst leaves ${P1AK_OWNER_INGRESS_ENABLED} as a literal Nginx
# variable and the entire public preview fails startup. Runtime Railway
# variables override these defaults after independent G2 acceptance.
ENV P1AK_OWNER_INGRESS_ENABLED=0 P1AO_GOOGLE_INGRESS_ENABLED=0 P1AP_DOCUMENTS_INGRESS_ENABLED=0 P1Q_PRIVATE_GATEWAY_SHARED_TOKEN=""
COPY nginx.railway.conf /etc/nginx/templates/default.conf.template
COPY nginx.owner-rate-zones.conf /etc/nginx/conf.d/00-personal-cfo-rates.conf
COPY owner-login.html owner-login.mjs owner-login.css /usr/share/nginx/html/
COPY index.html ui.css ui.mjs demo-data.mjs document-inbox.mjs owner-setup.mjs /usr/share/nginx/html/
COPY manifest.webmanifest sw.js pwa.mjs pwa.css /usr/share/nginx/html/
COPY icons/ /usr/share/nginx/html/icons/

EXPOSE 8080
