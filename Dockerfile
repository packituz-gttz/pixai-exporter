# Use AlmaLinux as the base image
FROM almalinux:9

# Set the working directory
WORKDIR /app

# Install necessary packages
RUN yum install -y \
    epel-release \
    && yum install -y \
    python3 \
    python3-pip \
    && yum clean all

COPY requirements/base.txt /requirements/
RUN pip install -r /requirements/base.txt
COPY app.py .

ENTRYPOINT ["pyinstaller", "--onefile", "--name", "pixai_exporter", "app.py"]
