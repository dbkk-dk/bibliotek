FROM python:3.9

# Force the stdout and stderr streams from python to be unbuffered. See
# https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED=1 \
  PYTHONPATH=/code/src/:$PYTHONPATH

# Ensure system user and install system depedencies
WORKDIR /code
COPY requirements.txt \
     src/
     ./

# hadolint ignore=DL3008,SC2046
RUN set -ex \
  # Add an image specific group and user.
  # Note: this is a system user/group, but have
  # UID/GID above the normal SYS_UID_MAX/SYS_GID_MAX of 999, but also above the
  # automatic ranges of UID_MAX/GID_MAX used by useradd/groupadd.
  # Hopefully there will be no conflicts with users of the
  # host system or users of other docker containers.
  && groupadd -g 73030 -r dbkk\
  && useradd -u 73030 --no-log-init -r -g dbkk \
  # Install system dependencies from file.
  && apt-get -y update \
  && apt-get -y install --no-install-recommends $(grep -oh '^[^#][[:alnum:].-]*' sys-requirements*.txt) \
  # clean up after apt-get and man-pages
  && apt-get clean && rm -rf "/var/lib/apt/lists/*" "/tmp/*" "/var/tmp/*" "/usr/share/man/??" "/usr/share/man/??_*"

# Set up to run given command as the new user
USER dbkk:dbkk

# ENTRYPOINT ["/code/docker/docker-entrypoint.sh"]
CMD ["explorer", "-h"]
