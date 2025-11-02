ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    && pip3 install --no-cache-dir \
    flask==3.0.0 \
    paho-mqtt==1.6.1 \
    requests==2.31.0

# Copy application files
COPY rootfs /

# Make run script executable
RUN chmod +x /usr/bin/run.sh
RUN chmod +x /usr/bin/app.py

# Set working directory
WORKDIR /usr/bin

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:8099/api/health || exit 1

# Labels
LABEL \
    io.hass.name="HID Remote Bridge" \
    io.hass.description="Monitor USB and Bluetooth HID devices and emit events to Home Assistant" \
    io.hass.arch="aarch64|amd64|armhf|armv7|i386" \
    io.hass.type="addon" \
    io.hass.version="0.1.0" \
    maintainer="Qutaiba Khader" \
    org.opencontainers.image.title="HID Remote Bridge" \
    org.opencontainers.image.description="Monitor HID devices and emit events" \
    org.opencontainers.image.vendor="Qutaiba Khader" \
    org.opencontainers.image.source="https://github.com/Qutaiba-Khader/qut-haos-addons" \
    org.opencontainers.image.licenses="MIT"

# Run
CMD ["/usr/bin/run.sh"]
