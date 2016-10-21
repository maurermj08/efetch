from setuptools import setup, find_packages

efetch_description = (
    u'Efetch is a web-based file explorer, viewer, and analyzer.'
)

setup(
    name=u'efetch',
    version=u'0.4 Beta',
    descript=efetch_description,
    packages=find_packages(),
    include_package_data=True,
    url=u'https://github.com/maurermj08/efetch_server',
    license=u'Apache License Version 2.0',
    author=u'Michael Maurer',
    classifiers=[
        u'Development Status :: 4 - Beta',
        u'Environment :: Web Environment',
        u'Operating System :: OS Independent',
        u'Programming Language :: Python',
    ],
    scripts=[u'efetch'],
    zip_safe=False,
    data_files=[(u'/etc', [u'efetch_plugins.yml'])],
    install_requires=frozenset([u'setuptools>=28.0.0',
                      u'elasticsearch>=2.0.0,<3.0.0',
                      u'argparse>=1.2.1',
                      u'bottle>=0.12.8',
                      u'dfvfs>=20150708',
                      u'elasticsearch>=2.1.0',
                      u'pefile>=1.2.10_139',
                      u'Yapsy>=1.11.223',
                      u'Pillow>=3.3.0',
                      u'Registry>=0.4.2',
                      u'python_magic>=0.4.12',
                      u'Requests>=2.10.0',
                      u'Rocket>=1.2.0',
                      u'ExifRead>=2.1.0',
                      u'Jinja2>=2.1',
                      u'rison>=1.0',
                      u'python-registry>=1.0']),
    dependency_links=[u'https://github.com/maurermj08/rison/tarball/master#egg=rison-1.1',
                      u'https://github.com/williballenthin/python-registry/tarball/master#egg=python-registry-1.2'],
    author_email=u'maurermj08@gmail.com',
)
