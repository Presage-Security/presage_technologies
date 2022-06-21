from setuptools import setup
requirements = ['requests']

__version__ = '1.0.0'

setup(
    name='Presage Technologies',
    version=__version__,
    packages=['presage_technologies'],
    package_dir={'presage_technologies': 'presage_technologies'},
    install_requires=requirements,
    zip_safe=False
)
