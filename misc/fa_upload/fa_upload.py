"""
Uploads a file to Efetch
"""

from yapsy.IPlugin import IPlugin


class FaUpload(IPlugin):
    def __init__(self):
        self.display_name = 'Upload'
        self.popularity = 0
        self.parent = False
        self.cache = False
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children):
        """Returns the result of this plugin to be displayed in a browser"""
        upload = False

        try:
            if request.old_query['upload'] and request.old_query['upload'] == 'True':
                upload = True
        except:
            pass

        if upload:
            return self.upload(helper, request)

        template = """
        <html>
        <head>
        <title>Upload</title>
        <style>
        form {
            position: absolute;
        }
        </style>
        </head>
        <body>
        <form action="/plugins/fa_upload/?upload=True" method="post" enctype="multipart/form-data">
        <fieldset>
            <legend>Upload a File</legend>
            Image ID:<br>
            <input type="text" name="name" />
            <br>
            <br>
            File:<br>
            <input type="file" name="data" />
            <br>
            <br>
            <br>
        <input type="submit" value="Start upload" />
        </fieldset>
        </form>
        </body>
        </html>
        """

        return template

    def upload(self, helper, request):
        image = request.forms.name
        data = request.files.data
        if image and data and data.file:
            # raw = data.file.read() # This is dangerous for big files
            filename = data.filename
            data.save(helper.upload_dir + filename)
            return '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=/plugins/fa_dfvfs/?image_id=' + image + '&path=' + helper.upload_dir + filename + '" /></head></html>'
            # return "Hello %s! You uploaded %s" % (image, filename)
        return "You missed a field."
