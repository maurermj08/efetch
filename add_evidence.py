import os
import logging
import sys
import getopt
import pytsk3
from utils.efetch_helper import EfetchHelper
from dfvfs_util import DfvfsUtil

def main(argv):
    try: 
        opts, args = getopt.getopt(argv, "hi:n:a:p:d", ["help", "image=", "name=", "address=", "port=", "output=", "debug"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    #MOVE DIRS TO HELPER (NOT CURR & OUTPUT)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    output_dir = curr_dir + "/cache/"
    upload_dir = curr_dir + "/uploads/"
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    image_path = ''
    image_id = ''
    address = 'localhost'
    port = '8080'
    max_download_size = 500

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-a", "--address"):
            address = arg
        elif opt in ("-p", "--port"):
            port = str(arg)
        elif opt in ("-i", "--image"):
            image_path = str(arg)
        elif opt in ("-n", "--name"):
            image_id = str(arg)
        elif opt in ('-d', "--debug"):
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.error("Unknown argument " + opt)
            usage()
            sys.exit(2)
    
    if not image_path:
        logging.error('Image and Image ID (name) are required')
        usage()
        sys.exit(2)
    if not image_id:
        logging.error('Image and Image ID (name) are required')
        usage()
        sys.exit(2)

    if not output_dir.endswith("/"):
        output_dir = output_dir + "/"
    if not os.path.isdir(output_dir):
        logging.error("Could not find output directory " + output_dir)
        sys.exit(2)

    #Initialize utils
    helper = EfetchHelper(curr_dir, output_dir, upload_dir, max_download_size * 1000000)
    test = helper.db_util
    manager = helper.plugin_manager

    add_image(image_id, 0, image_path, helper.db_util, address, port)

def add_image(image_id, offset, image_path, db_util, address, port):
    """Creates a file listing of the partition at the provided image and offset in the database"""
    if not str(image_path).startswith("/"):
        image_path = "/" + image_path

    if not os.path.isfile(image_path):
        logging.error("Could not find file at path '" + str(image_path) + "'")

    logging.info("Adding " + image_id + " to Elastic Search using dfVFS driver")

    offset = str(offset)

    #try:
    dfvfs_util = DfvfsUtil(image_path)
    index_name = 'efetch_timeline_' + image_id
    db_util.create_index(index_name)
    root = {
                '_index': index_name,
                '_type' : 'event',
                '_id' : image_id + '/' + offset + '/',
                '_source' : {
                    'id' : image_id + "/" + offset,
                    'pid' : image_id + '/' + offset + '/',
                    'iid' : image_id + '/' + offset + '/',
                    'image_id': image_id,
                    'offset' : offset,
                    'image_path' : image_path,
                    'name' : '/',
                    'path' : '/',
                    'ext' : '',
                    'dir' : '',
                    'file_type' : 'directory',
                    'inode' : '',
                    'mod' : 0,
                    'acc' : 0,
                    'chg' : 0,
                    'cre' : 0,
                    'size' : '',
                    'uid' : '',
                    'gid' : '',
                    'thumbnail' : "http://" + address + ":" + port + "/plguins/fa_thumbnail/" + image_id + "/" + offset + '/',
                    'analyze' : "http://" + address + ":" + port + "/plugins/fa_analyze/" + image_id + "/" + offset + '/',
                    'driver' : "fa_tsk"
                }
        }
    json = dfvfs_util.GetJson(image_id, offset, image_path, address, port)
    json.append(root)
    db_util.bulk(json)

def usage():
    print("usage: add_evidence.py [-h] [-i IMAGE] [-n NAME] [-a ADDRESS] [-p PORT] [-D DATABASE]")
    print("optional arguments:")
    print("  -h, --help         shows this help message and exits")
    print("  -i, --image        required path to the image to use")
    print("  -n, --name         required image id")
    print("  -a, --address      sets the IP address or hostname this server runs on, defaults to localhost")
    print("  -p, --port         sets the port this server runs on, defaults to 8080")
    print("  -d, --debug        displays debug output")
    print("")

if __name__=="__main__":
    main(sys.argv[1:])
