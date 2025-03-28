FROM postgres:17

# Install required packages
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libcurl4-openssl-dev \
    postgresql-server-dev-17 \
    && rm -rf /var/lib/apt/lists/*

# Clone and install pgsql-http extension
RUN git clone --branch master --single-branch https://github.com/pramsey/pgsql-http.git \
    && cd pgsql-http \
    && make \
    && make install \
    && cd .. \
    && rm -rf pgsql-http

# Add any additional configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf

CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]