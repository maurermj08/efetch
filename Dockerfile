FROM alpine
# dfvfs dependencies
RUN apk --no-cache add python2 py2-pip gcc python2-dev musl-dev xz-dev file g++
COPY dfvfs.requirements.txt .
RUN pip install -r dfvfs.requirements.txt
RUN pip install dfvfs pyliblzma libpff-python dtfabric

# efetch
WORKDIR /usr/local/src/
COPY . .
RUN apk --no-cache add zlib-dev jpeg-dev #pillow dependencies
RUN pip install requests pytz pyyaml bottle
RUN python setup.py build
RUN python setup.py install
