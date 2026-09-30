FROM python:3.12.14-slim
WORKDIR /fixture
COPY demo/service.py service.py
USER 65532:65532
EXPOSE 8000
CMD ["python", "service.py", "--host", "0.0.0.0"]
