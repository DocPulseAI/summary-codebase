from setuptools import setup, find_packages

setup(
    name="epic4",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "pydantic>=2.0.0",
        "requests>=2.31.0",
        "tenacity>=8.2.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "gcs": ["google-cloud-storage>=2.10.0"],
        "s3": ["boto3>=1.28.0"],
        "azure": ["azure-storage-blob>=12.20.0"],
        "cloud": ["google-cloud-storage>=2.10.0", "boto3>=1.28.0", "azure-storage-blob>=12.20.0"],
    },
)
