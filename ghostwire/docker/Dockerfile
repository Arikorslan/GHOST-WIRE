# GHOSTWIRE APK builder — Ubuntu 24.04 + JDK 17 + buildozer.
# Build:  docker build -t ghostwire-builder -f docker/Dockerfile .
# Run:    docker run --rm -v "$PWD/bin:/src/bin" ghostwire-builder
# Result: ./bin/ghostwire-1.1.0-arm64-v8a-debug.apk on the host.
#
# Apple Silicon Macs: add `--platform linux/amd64` to both commands
# (the Android SDK/NDK toolchains are x86_64-only; emulation works
# but is slower).
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    GRADLE_OPTS="-Xmx1500m -XX:MaxMetaspaceSize=512m" \
    KIVY_NO_ARGS=1
ENV PATH="$JAVA_HOME/bin:/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        git zip unzip autoconf libtool pkg-config \
        zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev \
        python3-pip openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --break-system-packages --no-cache-dir \
        buildozer cython \
    && buildozer --version && javac -version

WORKDIR /src
COPY . /src/

CMD ["/src/docker/build.sh"]
