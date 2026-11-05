# AmneziaWG Easy with the known session-auth panel patch
# (avoids 500 on /api/session after login).
FROM ghcr.io/spcfox/amnezia-wg-easy:development

USER root
RUN sed -i 's/this.req.session.authenticated/true/g' /app/server.js
