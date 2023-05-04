from setuptools import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
requirements = ['requests', 'presage_physiology_preprocessing==1.2.1']

__version__ = '1.4.2'

setup(
    name='Presage Technologies',
    version=__version__,
    packages=['presage_technologies'],
    author="Presage Technologies",
    author_email="support@presagetech.com",
    description="A Python client to interface with Presage Technologies' API services.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    package_dir={'presage_technologies': 'presage_technologies'},
    install_requires=requirements,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    url="https://physiology.presagetech.com/",
    project_urls={
        "Bug Tracker": "https://github.com/Presage-Security/presage_technologies/issues",
    },
)
