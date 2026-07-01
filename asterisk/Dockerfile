FROM andrius/asterisk:20

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        python3 \
        python3-pip \
        sox \
        asterisk-core-sounds-en \
        asterisk-core-sounds-en-gsm \
        asterisk-core-sounds-en-wav \
    && cp -rs /usr/share/asterisk/sounds/* /var/lib/asterisk/sounds/ \
    && pip3 install httpx --break-system-packages \
    && rm -rf /var/lib/apt/lists/*

COPY config/ /etc/asterisk/
COPY scripts/send_to_voice_api.py /usr/local/bin/send_to_voice_api.py
COPY scripts/voice_turn_agi.py /usr/local/bin/voice_turn_agi.py
RUN sed -i 's/\r$//' /usr/local/bin/send_to_voice_api.py /usr/local/bin/voice_turn_agi.py \
    && chmod +x /usr/local/bin/send_to_voice_api.py /usr/local/bin/voice_turn_agi.py

EXPOSE 5060/udp 5060/tcp 10000-10100/udp
