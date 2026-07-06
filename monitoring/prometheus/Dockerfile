FROM prom/prometheus:v2.54.1

COPY prometheus.yml /etc/prometheus/prometheus.yml

EXPOSE 8080

CMD [
  "--config.file=/etc/prometheus/prometheus.yml",
  "--web.listen-address=0.0.0.0:8080"
]
