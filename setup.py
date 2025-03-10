import setuptools

long_description = ""
with open("README.md", "r") as fh:
    long_description = fh.read()
assert long_description

setuptools.setup(
    name="thor-requests",
    version="1.2.2",
    author="laalaguer",
    author_email="laalaguer@gmail.com",
    description="Simple network VeChain SDK for human to interact with the blockchain",
    keywords="vechain thor blockchain sdk requests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    url="https://github.com/laalaguer/thor-requests",
    project_urls={
        "Documentation": "https://github.com/laalaguer/thor-requests",
        "Source": "https://github.com/laalaguer/thor-requests",
        "Issue Tracker": "https://github.com/laalaguer/thor-requests/issues",
    },
    python_requires=">=3.6",
    install_requires=[x.strip() for x in open("requirements.txt")],
    packages=setuptools.find_packages(),
)
