FROM python:3.12.12-slim
WORKDIR /app
COPY app.py engine.py configuration.py ./
COPY static ./static
RUN useradd --system --uid 10001 radar && mkdir /data && chown radar /data
USER radar
ENV RADAR_DATA=/data RADAR_HOST=0.0.0.0 RADAR_PORT=8765
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8765/api/health',headers={'Authorization':'Bearer '+os.environ['RADAR_TOKEN']}); urllib.request.urlopen(r,timeout=2)"
CMD ["python", "app.py"]
