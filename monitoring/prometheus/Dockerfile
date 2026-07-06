FROM prom/prometheus:v2.54.1

COPY prometheus.yml /etc/prometheus/prometheus.yml

EXPOSE 9090

ENTRYPOINT ["/bin/sh","-c"]
CMD exec /bin/prometheus --config.file=/etc/prometheus/prometheus.yml --web.listen-address=0.0.0.0:${PORT:-9090}
