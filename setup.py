import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


with open("requirements.txt") as fh:
    requirements = fh.read().splitlines()


setuptools.setup(
    name="smart_tv_telegram",
    version="1.0.2.dev0",
    author="andrew-ld",
    author_email="andrew-ld@protonmail.com",
    description="A Telegram Bot to stream content on your smart TV",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/andrew-ld/smart-tv-telegram",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Operating System :: OS Independent",
    ],
    install_requires=requirements,
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "smart_tv_telegram=smart_tv_telegram.__main__:arg_parser"
        ],
    }
)
