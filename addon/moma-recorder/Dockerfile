ARG BUILD_FROM
FROM ${BUILD_FROM}

# De protocollaag gebruikt uitsluitend de standaardbibliotheek, dus dit is de
# enige afhankelijkheid.
RUN apk add --no-cache python3

# Deze twee komen uit `python tools/sync_addon.py` -- Docker kan niet buiten
# zijn buildcontext kijken.
COPY protocol /opt/moma/protocol
COPY moma_record.py /opt/moma/moma_record.py

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
