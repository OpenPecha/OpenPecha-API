FROM tiangolo/uvicorn-gunicorn:python3.8

WORKDIR /app/

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install calibre deps
RUN : \
    && apt-get clean \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    --no-install-recommends \
    libgl1-mesa-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/list/* \
    && :


# install calibre
# RUN wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin
# RUN ebook-convert --version

# install monlam fonts
RUN mkdir /usr/share/fonts/truetype/monlam
RUN wget https://github.com/OpenPecha/ebook-template/raw/master/monlam_uni_ouchan2.ttf
RUN mv monlam_uni_ouchan2.ttf /usr/share/fonts/truetype/monlam/

# Install pandoc
RUN apt-get install -y pandoc

# Install Poetry 
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3
ENV PATH="/opt/poetry/bin:$PATH"
RUN poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./app/pyproject.toml ./app/poetry.lock* /app/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --no-dev ; fi"

# Setup gitub config
RUN : \
    && git config --global user.email "dev@openpecha.org" \
    && git config --global user.name "openpecha" \
    && :

COPY ./app /app
ENV PYTHONPATH=/app
