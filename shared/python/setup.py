"""Setup file for the svaani_common shared package."""

from setuptools import setup, find_packages

setup(
    name="svaani-common",
    version="0.1.0",
    description="Shared libraries for Svaani medical AI microservices",
    author="Svaani Team",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "confluent-kafka>=2.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "mypy>=1.7",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)

# minor shared lib update
