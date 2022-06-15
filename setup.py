from setuptools import setup
requirements = ['requests']


setup(
    name='Presage Technologies',
    version='1.0.1',
    packages=['presage_technologies'],
    package_dir={'presage_technologies': 'presage_technologies'},
    install_requires=requirements,
    zip_safe=False
)
