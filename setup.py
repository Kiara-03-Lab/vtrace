from setuptools import setup, find_packages

setup(
    name="vtrace",
    version="0.1.0",
    description="Reproducible traces for AI-assisted coding",
    author="Your Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "vtrace=vtrace.cli:main",
        ],
    },
    description="Reproducible traces for vibe coding sessions",
    author="Your Team",
    packages=find_packages(),
    package_dir={"vtrace": "src"},
    install_requires=["pyyaml>=6.0"],
    entry_points={
        "console_scripts": [
            "vtrace=src.cli:main",
        ],
    },
    python_requires=">=3.8",
)
