import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

def read_requirements(file):
    with open(file, "r") as fh:
        return fh.read().splitlines()
    
# Read requirements from the requirements.txt file
requirements = read_requirements("requirements.txt")



setuptools.setup(
    name="flamapy-configurator",
    version="2.0.1",
    author="Flamapy",
    author_email="flamapy@us.es",
    description="configurator-plugin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_namespace_packages(include=['flamapy.*']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    install_requires=requirements,
)