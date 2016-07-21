from distutils.core import setup

setup(
    name='efetch',
    version='0.6 Alpha',
    packages=['', 'utils'],
    url='https://github.com/maurermj08/efetch',
    license='Apache License Version 2.0',
    author='Michael Maurer',
    install_requires=['argparse>=1.2.1',
                      'bottle>=0.12.8',
                      'dfvfs>=20150708',
                      'elasticsearch>=2.1.0',
                      'pefile>=1.2.10_139',
                      'Yapsy>=1.11.223',
                      'Pillow>=3.3.0',
                      'Registry>=0.4.2',
                      'python_magic>=0.4.12',
                      'Requests>=2.10.0',
                      'cherrypy>=5.0.0',
                      'ExifRead>=2.1.0',
                      'rison>=1.0',
                      'python-registry>=1.0'],
    dependency_links=['https://github.com/maurermj08/rison/tarball/master#egg=rison-1.1',
                      'https://github.com/williballenthin/python-registry/tarball/master#egg=python-registry-1.2'],
    author_email='maurermj08@gmail.com',
    description='A pathspec viewer RESTful API'
)
